import logging
import os
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum
from django.core.cache import cache

# Modelos para coletar dados
from controle_diario.models import ControleDiario, RelatorioDiarioSine
from escolas.models import Escola
from alunos.models import Aluno
from cursos.models import Inscricao

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envia o consolidado do Controle Diário por e-mail para a administração'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignora a verificação de agendamento e envia o e-mail imediatamente.',
        )

    def handle(self, *args, **options):
        from core.models import AgendamentoEmail

        # Verificar agendamento (a menos que --force seja usado)
        is_force = options.get('force')
        if not is_force:
            agendamento = AgendamentoEmail.get_config()
            if not agendamento.deve_enviar_agora():
                self.stdout.write(self.style.NOTICE(
                    'Envio ignorado: fora do horário/dia configurado. Use --force para forçar o envio.'
                ))
                return
            # Guarda anti-duplicata: ignora se já enviou hoje
            hoje_str = timezone.localtime(timezone.now()).date().isoformat()
            cache_key = f'email_resumo_diario_sent_{hoje_str}'
            if cache.get(cache_key):
                self.stdout.write(self.style.NOTICE(
                    'Envio ignorado: e-mail de resumo já foi enviado hoje.'
                ))
                return

        self.stdout.write(self.style.WARNING('Iniciando rotina de envio do relatório do Controle Diário...'))
        
        hoje = timezone.localtime(timezone.now()).date()
        inicio_dia = timezone.make_aware(timezone.datetime.combine(hoje, timezone.datetime.min.time()))
        fim_dia = timezone.make_aware(timezone.datetime.combine(hoje, timezone.datetime.max.time()))
        
        # 1. Coleta dos registros de Controle Diário do dia
        controles_dia = ControleDiario.objects.filter(data=hoje).select_related('escola', 'usuario')
        sine_dia = RelatorioDiarioSine.objects.filter(data=hoje).first()
        
        # Separando por tipo de escola
        controles_cp = controles_dia.filter(escola__tipo='CP')
        controles_uditech = controles_dia.filter(escola__tipo='UDITECH')
        
        # Cálculo dos Totais Consolidados CP
        totais_cp = controles_cp.aggregate(
            total_atendimento=Sum('atendimento'),
            total_inscricoes=Sum('inscricoes'),
            total_presentes=Sum('pessoas_presentes'),
            total_recebidas=Sum('ligacoes_recebidas'),
            total_realizadas=Sum('ligacoes_realizadas')
        )
        total_atendimento_cp = totais_cp['total_atendimento'] or 0
        total_inscricoes_cp = totais_cp['total_inscricoes'] or 0
        total_presentes_cp = totais_cp['total_presentes'] or 0
        total_recebidas_cp = totais_cp['total_recebidas'] or 0
        total_realizadas_cp = totais_cp['total_realizadas'] or 0

        # Cálculo dos Totais Consolidados Uditech
        totais_uditech = controles_uditech.aggregate(
            total_atendimento=Sum('atendimento'),
            total_inscricoes=Sum('inscricoes'),
            total_presentes=Sum('pessoas_presentes'),
            total_recebidas=Sum('ligacoes_recebidas'),
            total_realizadas=Sum('ligacoes_realizadas')
        )
        total_atendimento_uditech = totais_uditech['total_atendimento'] or 0
        total_inscricoes_uditech = totais_uditech['total_inscricoes'] or 0
        total_presentes_uditech = totais_uditech['total_presentes'] or 0
        total_recebidas_uditech = totais_uditech['total_recebidas'] or 0
        total_realizadas_uditech = totais_uditech['total_realizadas'] or 0

        # Escolas Pendentes
        escolas_que_enviaram = controles_dia.values_list('escola_id', flat=True)
        escolas_pendentes_cp = Escola.objects.filter(tipo='CP').exclude(id__in=escolas_que_enviaram).order_by('nome')
        escolas_pendentes_uditech = Escola.objects.filter(tipo='UDITECH').exclude(id__in=escolas_que_enviaram).order_by('nome')

        # 5. Configurar Destinatário(s)
        # Busca primeiramente os destinatários cadastrados na interface do sistema
        from core.models import EmailDestinatario
        destinatarios_db = list(
            EmailDestinatario.objects.filter(ativo=True).values('nome', 'email', 'receber_cp', 'receber_uditech', 'receber_sine')
        )

        if destinatarios_db:
            destinatarios_lista = destinatarios_db
        else:
            # Fallback para o .env se a lista do banco estiver vazia
            email_admin = os.getenv('EMAIL_ADMIN_RECEIVER')
            if not email_admin or email_admin in ['onboarding@resend.dev', 'resend', '']:
                email_admin = 'klismanrds@gmail.com'
            destinatarios_lista = [{
                'nome': 'Administrador', 
                'email': email_admin,
                'receber_cp': True,
                'receber_uditech': True,
                'receber_sine': True
            }]
            self.stdout.write(self.style.WARNING(
                'Nenhum destinatário ativo no banco. Usando fallback do .env: ' + str(destinatarios_lista)
            ))

        assunto = f"Controle Diário - {hoje.strftime('%d/%m/%Y')}"

        MESES_PT = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                     'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        
        # 6. Geração dos Blocos HTML e Texto Simples para cada tipo de dado

        # --- SEÇÃO CP ---
        # Tabela CP
        linhas_tabela_cp = ""
        if controles_cp.exists():
            for c in controles_cp:
                usuario_nome = c.usuario.get_full_name() if c.usuario and c.usuario.get_full_name() else (c.usuario.username if c.usuario else "Sistema")
                linhas_tabela_cp += f"""
                <tr>
                    <td><strong>{c.escola.nome}</strong></td>
                    <td class="text-center">{c.atendimento}</td>
                    <td class="text-center">{c.inscricoes}</td>
                    <td class="text-center">{c.pessoas_presentes}</td>
                    <td class="text-center">{c.ligacoes_recebidas}</td>
                    <td class="text-center">{c.ligacoes_realizadas}</td>
                    <td><span class="user-pill">{usuario_nome}</span></td>
                </tr>
                """
        else:
            linhas_tabela_cp = """
            <tr>
                <td colspan="7" class="text-center text-muted" style="padding: 30px 10px;">
                    Nenhum controle diário foi enviado pelos CPs até o momento hoje.
                </td>
            </tr>
            """

        escolas_pendentes_cp_html = ""
        if escolas_pendentes_cp.exists():
            for esc in escolas_pendentes_cp:
                coordenador = esc.coordenador_user.get_full_name() if esc.coordenador_user else "Não atribuído"
                escolas_pendentes_cp_html += f"""
                <li class="pendente-item">
                    <div>
                        <strong>{esc.nome}</strong>
                        <div class="coordenador-sub">Coord: {coordenador}</div>
                    </div>
                    <span class="status-warning">Pendente</span>
                </li>
                """
        else:
            escolas_pendentes_cp_html = """
            <li class="pendente-item text-center text-success" style="justify-content: center; padding: 15px 0;">
                🎉 Todos os CPs enviaram o controle diário de hoje!
            </li>
            """

        # --- SEÇÃO UDITECH ---
        # Tabela Uditech
        linhas_tabela_uditech = ""
        if controles_uditech.exists():
            for c in controles_uditech:
                usuario_nome = c.usuario.get_full_name() if c.usuario and c.usuario.get_full_name() else (c.usuario.username if c.usuario else "Sistema")
                linhas_tabela_uditech += f"""
                <tr>
                    <td><strong>{c.escola.nome}</strong></td>
                    <td class="text-center">{c.atendimento}</td>
                    <td class="text-center">{c.inscricoes}</td>
                    <td class="text-center">{c.pessoas_presentes}</td>
                    <td class="text-center">{c.ligacoes_recebidas}</td>
                    <td class="text-center">{c.ligacoes_realizadas}</td>
                    <td><span class="user-pill">{usuario_nome}</span></td>
                </tr>
                """
        else:
            linhas_tabela_uditech = """
            <tr>
                <td colspan="7" class="text-center text-muted" style="padding: 30px 10px;">
                    Nenhum controle diário foi enviado pelas Uditechs até o momento hoje.
                </td>
            </tr>
            """

        escolas_pendentes_uditech_html = ""
        if escolas_pendentes_uditech.exists():
            for esc in escolas_pendentes_uditech:
                coordenador = esc.coordenador_user.get_full_name() if esc.coordenador_user else "Não atribuído"
                escolas_pendentes_uditech_html += f"""
                <li class="pendente-item">
                    <div>
                        <strong>{esc.nome}</strong>
                        <div class="coordenador-sub">Coord: {coordenador}</div>
                    </div>
                    <span class="status-warning">Pendente</span>
                </li>
                """
        else:
            escolas_pendentes_uditech_html = """
            <li class="pendente-item text-center text-success" style="justify-content: center; padding: 15px 0;">
                🎉 Todas as Uditechs enviaram o controle diário de hoje!
            </li>
            """

        # Construindo blocos de HTML

        html_cp_block = f"""
        <!-- SEÇÃO CP -->
        <div style="margin-top: 30px; border-top: 3px solid #1e3a8a; padding-top: 20px;">
            <h2 class="section-title success-line" style="border-left-color: #1e3a8a; color: #1e3a8a;">Centros Profissionalizantes (CP)</h2>
            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-title">Atendimentos</div>
                    <div class="kpi-val">{total_atendimento_cp}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Inscrições</div>
                    <div class="kpi-val">{total_inscricoes_cp}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Presentes</div>
                    <div class="kpi-val">{total_presentes_cp}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Ligs. Recebidas</div>
                    <div class="kpi-val">{total_recebidas_cp}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Ligs. Realizadas</div>
                    <div class="kpi-val">{total_realizadas_cp}</div>
                </div>
            </div>

            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Unidade / Escola</th>
                            <th class="text-center">Atend.</th>
                            <th class="text-center">Insc.</th>
                            <th class="text-center">Pres.</th>
                            <th class="text-center">Lig. Rec.</th>
                            <th class="text-center">Lig. Real.</th>
                            <th>Lançado por</th>
                        </tr>
                    </thead>
                    <tbody>
                        {linhas_tabela_cp}
                        <tr class="total-row">
                            <td>TOTAL CP</td>
                            <td class="text-center">{total_atendimento_cp}</td>
                            <td class="text-center">{total_inscricoes_cp}</td>
                            <td class="text-center">{total_presentes_cp}</td>
                            <td class="text-center">{total_recebidas_cp}</td>
                            <td class="text-center">{total_realizadas_cp}</td>
                            <td>-</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h3 style="font-size: 13px; font-weight: 700; color: #b91c1c; margin-bottom: 8px;">Pendências de Envio - CP</h3>
            <ul class="pendentes-list">
                {escolas_pendentes_cp_html}
            </ul>
        </div>
        """

        html_uditech_block = f"""
        <!-- SEÇÃO UDITECH -->
        <div style="margin-top: 40px; border-top: 3px solid #f59e0b; padding-top: 20px;">
            <h2 class="section-title success-line" style="border-left-color: #f59e0b; color: #b45309;">Unidades Uditech</h2>
            <div class="kpi-container">
                <div class="kpi-card" style="border-color: #fde68a; background: #fffbeb;">
                    <div class="kpi-title" style="color: #b45309;">Atendimentos</div>
                    <div class="kpi-val" style="color: #b45309;">{total_atendimento_uditech}</div>
                </div>
                <div class="kpi-card" style="border-color: #fde68a; background: #fffbeb;">
                    <div class="kpi-title" style="color: #b45309;">Inscrições</div>
                    <div class="kpi-val" style="color: #b45309;">{total_inscricoes_uditech}</div>
                </div>
                <div class="kpi-card" style="border-color: #fde68a; background: #fffbeb;">
                    <div class="kpi-title" style="color: #b45309;">Presentes</div>
                    <div class="kpi-val" style="color: #b45309;">{total_presentes_uditech}</div>
                </div>
                <div class="kpi-card" style="border-color: #fde68a; background: #fffbeb;">
                    <div class="kpi-title" style="color: #b45309;">Ligs. Recebidas</div>
                    <div class="kpi-val" style="color: #b45309;">{total_recebidas_uditech}</div>
                </div>
                <div class="kpi-card" style="border-color: #fde68a; background: #fffbeb;">
                    <div class="kpi-title" style="color: #b45309;">Ligs. Realizadas</div>
                    <div class="kpi-val" style="color: #b45309;">{total_realizadas_uditech}</div>
                </div>
            </div>

            <div class="table-responsive">
                <table>
                    <thead>
                        <tr style="background-color: #fffbeb;">
                            <th style="color: #b45309;">Unidade / Escola</th>
                            <th class="text-center" style="color: #b45309;">Atend.</th>
                            <th class="text-center" style="color: #b45309;">Insc.</th>
                            <th class="text-center" style="color: #b45309;">Pres.</th>
                            <th class="text-center" style="color: #b45309;">Lig. Rec.</th>
                            <th class="text-center" style="color: #b45309;">Lig. Real.</th>
                            <th style="color: #b45309;">Lançado por</th>
                        </tr>
                    </thead>
                    <tbody>
                        {linhas_tabela_uditech}
                        <tr class="total-row" style="background-color: #fef3c7; border-top: 2px solid #f59e0b; color: #78350f;">
                            <td>TOTAL UDITECH</td>
                            <td class="text-center">{total_atendimento_uditech}</td>
                            <td class="text-center">{total_inscricoes_uditech}</td>
                            <td class="text-center">{total_presentes_uditech}</td>
                            <td class="text-center">{total_recebidas_uditech}</td>
                            <td class="text-center">{total_realizadas_uditech}</td>
                            <td>-</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h3 style="font-size: 13px; font-weight: 700; color: #b91c1c; margin-bottom: 8px;">Pendências de Envio - Uditech</h3>
            <ul class="pendentes-list">
                {escolas_pendentes_uditech_html}
            </ul>
        </div>
        """

        html_sine_block = ""
        if sine_dia:
            total_atendimentos_sine = (
                sine_dia.atendimento_trabalhador + sine_dia.atendimento_trabalhador_online +
                sine_dia.atendimento_empregador + sine_dia.atendimento_empregador_online
            )
            html_sine_block = f"""
            <!-- SEÇÃO SINE -->
            <div style="margin-top: 40px; border-top: 3px solid #10b981; padding-top: 20px;">
                <h2 class="section-title success-line" style="border-left-color: #10b981; color: #065f46;">Indicadores do SINE</h2>
                <div class="kpi-container">
                    <div class="kpi-card" style="border-color: #a7f3d0; background: #f0fdf4;">
                        <div class="kpi-title" style="color: #047857;">Atendimentos</div>
                        <div class="kpi-val" style="color: #065f46;">{total_atendimentos_sine}</div>
                    </div>
                    <div class="kpi-card" style="border-color: #a7f3d0; background: #f0fdf4;">
                        <div class="kpi-title" style="color: #047857;">Vagas Captadas</div>
                        <div class="kpi-val" style="color: #065f46;">{sine_dia.vagas_captadas}</div>
                    </div>
                    <div class="kpi-card" style="border-color: #a7f3d0; background: #f0fdf4;">
                        <div class="kpi-title" style="color: #047857;">Seguro Desemp.</div>
                        <div class="kpi-val" style="color: #065f46;">{sine_dia.seguro_desemprego}</div>
                    </div>
                    <div class="kpi-card" style="border-color: #a7f3d0; background: #f0fdf4;">
                        <div class="kpi-title" style="color: #047857;">Entrevistados</div>
                        <div class="kpi-val" style="color: #065f46;">{sine_dia.entrevistados}</div>
                    </div>
                </div>

                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr style="background-color: #f0fdf4;">
                                <th style="color: #047857;">Indicador / Serviço</th>
                                <th class="text-center" style="color: #047857;">Valor Registrado</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Atendimento ao Trabalhador (Presencial)</td>
                                <td class="text-center">{sine_dia.atendimento_trabalhador}</td>
                            </tr>
                            <tr>
                                <td>Atendimento ao Trabalhador (On-line)</td>
                                <td class="text-center">{sine_dia.atendimento_trabalhador_online}</td>
                            </tr>
                            <tr>
                                <td>Atendimento ao Empregador (Presencial)</td>
                                <td class="text-center">{sine_dia.atendimento_empregador}</td>
                            </tr>
                            <tr>
                                <td>Atendimento ao Empregador (On-line)</td>
                                <td class="text-center">{sine_dia.atendimento_empregador_online}</td>
                            </tr>
                            <tr>
                                <td>Seguro Desemprego</td>
                                <td class="text-center">{sine_dia.seguro_desemprego}</td>
                            </tr>
                            <tr>
                                <td>CTPS Digital</td>
                                <td class="text-center">{sine_dia.ctps_digital}</td>
                            </tr>
                            <tr>
                                <td>Vagas Captadas</td>
                                <td class="text-center">{sine_dia.vagas_captadas}</td>
                            </tr>
                            <tr>
                                <td>Currículos Recebidos</td>
                                <td class="text-center">{sine_dia.curriculos}</td>
                            </tr>
                            <tr>
                                <td>Entrevistados</td>
                                <td class="text-center">{sine_dia.entrevistados}</td>
                            </tr>
                            <tr>
                                <td>Processos Seletivos Realizados</td>
                                <td class="text-center">{sine_dia.processo_seletivo}</td>
                            </tr>
                            <tr>
                                <td>Orientação Profissional</td>
                                <td class="text-center">{sine_dia.orientacao_profissional}</td>
                            </tr>
                            <tr>
                                <td>Ligações Recebidas</td>
                                <td class="text-center">{sine_dia.ligacoes_recebidas}</td>
                            </tr>
                            <tr>
                                <td>Ligações Realizadas</td>
                                <td class="text-center">{sine_dia.ligacoes_realizadas}</td>
                            </tr>
                            <tr class="total-row" style="background-color: #d1fae5; border-top: 2px solid #10b981; color: #065f46;">
                                <td>TOTAL DE PROCEDIMENTOS SINE</td>
                                <td class="text-center">{sine_dia.total_procedimentos}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            """
        else:
            html_sine_block = """
            <!-- SEÇÃO SINE -->
            <div style="margin-top: 40px; border-top: 3px solid #10b981; padding-top: 20px;">
                <h2 class="section-title success-line" style="border-left-color: #10b981; color: #065f46;">Indicadores do SINE</h2>
                <p style="padding: 20px 0; text-align: center; color: #64748b; font-style: italic;">
                    Nenhum indicador do SINE foi enviado hoje até o momento.
                </p>
            </div>
            """

        # Envio Individual com personalização de preferências
        from_email_config = getattr(settings, 'DEFAULT_FROM_EMAIL', 'sistema@gestaoqualificacao.com.br')
        
        sucessos = []
        for dest in destinatarios_lista:
            nome_dest = dest.get('nome', 'Equipe')
            email_dest = dest.get('email')
            
            receber_cp = dest.get('receber_cp', True)
            receber_uditech = dest.get('receber_uditech', True)
            receber_sine = dest.get('receber_sine', True)

            # Construir texto simples personalizado
            texto_list = [f"Controle Diário do dia {hoje.day} de {MESES_PT[hoje.month - 1]} de {hoje.year}:\n"]
            if receber_cp:
                texto_list.append(
                    f"\n--- TOTAIS DO DIA (CP) ---\n"
                    f"Atendimentos: {total_atendimento_cp}\n"
                    f"Inscrições: {total_inscricoes_cp}\n"
                    f"Presentes: {total_presentes_cp}\n"
                )
            if receber_uditech:
                texto_list.append(
                    f"\n--- TOTAIS DO DIA (UDITECH) ---\n"
                    f"Atendimentos: {total_atendimento_uditech}\n"
                    f"Inscrições: {total_inscricoes_uditech}\n"
                    f"Presentes: {total_presentes_uditech}\n"
                )
            if receber_sine and sine_dia:
                texto_list.append(
                    f"\n--- TOTAIS DO SINE ---\n"
                    f"Atendimentos Trabalhador: {sine_dia.atendimento_trabalhador + sine_dia.atendimento_trabalhador_online}\n"
                    f"Vagas Captadas: {sine_dia.vagas_captadas}\n"
                    f"Total Procedimentos: {sine_dia.total_procedimentos}\n"
                )
            texto_list.append("\nVerifique o e-mail em formato HTML para visualizar os dados formatados.")
            texto_personalizado = "".join(texto_list)

            # Construir HTML personalizado
            html_body_parts = []
            if receber_cp:
                html_body_parts.append(html_cp_block)
            if receber_uditech:
                html_body_parts.append(html_uditech_block)
            if receber_sine:
                html_body_parts.append(html_sine_block)

            corpo_dados_html = "".join(html_body_parts)

            # Estrutura base do HTML
            html_personalizado = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
                        background-color: #f3f4f6;
                        color: #1f2937;
                        margin: 0;
                        padding: 0;
                        -webkit-font-smoothing: antialiased;
                    }}
                    .wrapper {{
                        background-color: #f3f4f6;
                        padding: 30px 15px;
                    }}
                    .container {{
                        max-width: 800px;
                        background: #ffffff;
                        margin: 0 auto;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
                        border: 1px solid #e5e7eb;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
                        color: #ffffff;
                        padding: 35px 25px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 26px;
                        font-weight: 800;
                        letter-spacing: -0.5px;
                    }}
                    .header p {{
                        margin: 8px 0 0 0;
                        opacity: 0.9;
                        font-size: 15px;
                    }}
                    .content {{
                        padding: 35px 30px;
                    }}
                    
                    /* Grid de Resumo Visual (Kpi Cards) */
                    .kpi-container {{
                        display: table;
                        width: 100%;
                        table-layout: fixed;
                        margin-bottom: 25px;
                        border-spacing: 8px 0;
                    }}
                    .kpi-card {{
                        display: table-cell;
                        background: #f8fafc;
                        border: 1px solid #e2e8f0;
                        border-radius: 10px;
                        padding: 12px 6px;
                        text-align: center;
                        vertical-align: middle;
                    }}
                    .kpi-title {{
                        font-size: 10px;
                        font-weight: 700;
                        text-transform: uppercase;
                        color: #64748b;
                        margin-bottom: 5px;
                    }}
                    .kpi-val {{
                        font-size: 18px;
                        font-weight: 800;
                        color: #1e3a8a;
                    }}

                    /* Tabela estilizada */
                    .table-responsive {{
                        width: 100%;
                        overflow-x: auto;
                        margin-bottom: 30px;
                        border-radius: 8px;
                        border: 1px solid #e5e7eb;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        text-align: left;
                        font-size: 14px;
                    }}
                    th {{
                        background-color: #f8fafc;
                        color: #475569;
                        font-weight: 700;
                        padding: 10px 12px;
                        border-bottom: 2px solid #e5e7eb;
                        text-transform: uppercase;
                        font-size: 10px;
                    }}
                    td {{
                        padding: 12px;
                        border-bottom: 1px solid #f0f2f5;
                        vertical-align: middle;
                    }}
                    tr:last-child td {{
                        border-bottom: none;
                    }}
                    tr.total-row td {{
                        background-color: #f1f5f9;
                        font-weight: 700;
                        border-top: 2px solid #cbd5e1;
                        border-bottom: 2px solid #cbd5e1;
                        color: #0f172a;
                    }}
                    .text-center {{
                        text-align: center;
                    }}
                    
                    /* Badges e Pílulas */
                    .badge {{
                        display: inline-block;
                        font-size: 9px;
                        font-weight: 800;
                        padding: 2px 6px;
                        border-radius: 4px;
                        margin-top: 4px;
                    }}
                    .badge-uditech {{
                        background-color: #dbeafe;
                        color: #1e40af;
                    }}
                    .badge-cp {{
                        background-color: #fef3c7;
                        color: #92400e;
                    }}
                    .user-pill {{
                        display: inline-block;
                        background-color: #f1f5f9;
                        color: #475569;
                        padding: 4px 8px;
                        border-radius: 100px;
                        font-size: 11px;
                        font-weight: 500;
                    }}
                    
                    /* Seção de pendências */
                    .section-title {{
                        font-size: 15px;
                        font-weight: 700;
                        color: #0f172a;
                        margin-top: 0;
                        margin-bottom: 15px;
                        border-left: 4px solid #ef4444;
                        padding-left: 10px;
                    }}
                    .section-title.success-line {{
                        border-left-color: #1e3a8a;
                    }}
                    .pendentes-list {{
                        list-style: none;
                        padding: 0;
                        margin: 0;
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        background-color: #ffffff;
                    }}
                    .pendente-item {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 10px 16px;
                        border-bottom: 1px solid #f0f2f5;
                    }}
                    .pendente-item:last-child {{
                        border-bottom: none;
                    }}
                    .coordenador-sub {{
                        font-size: 11px;
                        color: #64748b;
                        margin-top: 2px;
                    }}
                    .status-warning {{
                        font-size: 10px;
                        font-weight: 700;
                        color: #b91c1c;
                        background-color: #fef2f2;
                        padding: 2px 8px;
                        border-radius: 100px;
                    }}

                    .footer {{
                        background: #f8fafc;
                        text-align: center;
                        padding: 25px;
                        font-size: 12px;
                        color: #64748b;
                        border-top: 1px solid #e5e7eb;
                    }}
                </style>
            </head>
            <body>
                <div class="wrapper">
                    <div class="container">
                        <div class="header">
                            <h1>Controle Diário</h1>
                            <p>Consolidado Operacional de {hoje.strftime('%d')} de {MESES_PT[hoje.month - 1]} de {hoje.year}</p>
                        </div>
                        <div class="content">
                            <p style="font-size: 15px; color: #334155; margin-bottom: 25px; line-height: 1.5;">
                                Olá, <strong>{nome_dest}</strong><br>
                                Segue o relatório de controle diário consolidado das atividades.
                            </p>
                            
                            {corpo_dados_html}

                        </div>
                        <div class="footer">
                            &copy; {hoje.year} Diretoria de Qualificação Profissional. <br>
                            Relatório gerado automaticamente pelo sistema de Gestão Qualificação Profissional
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            try:
                msg = EmailMultiAlternatives(
                    subject=assunto,
                    body=texto_personalizado,
                    from_email=from_email_config,
                    to=[email_dest]
                )
                msg.attach_alternative(html_personalizado, "text/html")
                msg.send()
                sucessos.append(email_dest)
            except Exception as e:
                logger.exception(f"Falha ao enviar e-mail de resumo diário para {email_dest}.")
                self.stdout.write(self.style.ERROR(f'Erro ao enviar e-mail para {email_dest}: {str(e)}'))
        
        if sucessos:
            self.stdout.write(self.style.SUCCESS(f'Sucesso: E-mail de resumo diário enviado para {sucessos}'))
            if not is_force:
                hoje_str = timezone.localtime(timezone.now()).date().isoformat()
                cache_key = f'email_resumo_diario_sent_{hoje_str}'
                cache.set(cache_key, True, timeout=86400)
