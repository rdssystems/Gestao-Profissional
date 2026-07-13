import logging
import os
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum
from django.core.cache import cache

# Modelos para coletar dados
from controle_diario.models import ControleDiario
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
        
        # 2. Cálculo dos Totais Consolidados (sugestão do sistema)
        totais = controles_dia.aggregate(
            total_atendimento=Sum('atendimento'),
            total_inscricoes=Sum('inscricoes'),
            total_presentes=Sum('pessoas_presentes'),
            total_recebidas=Sum('ligacoes_recebidas'),
            total_realizadas=Sum('ligacoes_realizadas')
        )
        
        total_atendimento = totais['total_atendimento'] or 0
        total_inscricoes = totais['total_inscricoes'] or 0
        total_presentes = totais['total_presentes'] or 0
        total_recebidas = totais['total_recebidas'] or 0
        total_realizadas = totais['total_realizadas'] or 0



        # 4. Escolas Pendentes (Sugestão de controle para o administrador saber quem não enviou)
        escolas_que_enviaram = controles_dia.values_list('escola_id', flat=True)
        escolas_pendentes = Escola.objects.exclude(id__in=escolas_que_enviaram).order_by('tipo', 'nome')

        # 5. Configurar Destinatário(s)
        # Busca primeiramente os destinatários cadastrados na interface do sistema
        from core.models import EmailDestinatario
        destinatarios_db = list(
            EmailDestinatario.objects.filter(ativo=True).values('nome', 'email')
        )

        if destinatarios_db:
            destinatarios_lista = destinatarios_db
        else:
            # Fallback para o .env se a lista do banco estiver vazia
            email_admin = os.getenv('EMAIL_ADMIN_RECEIVER')
            if not email_admin or email_admin in ['onboarding@resend.dev', 'resend', '']:
                email_admin = 'klismanrds@gmail.com'
            destinatarios_lista = [{'nome': 'Administrador', 'email': email_admin}]
            self.stdout.write(self.style.WARNING(
                'Nenhum destinatário ativo no banco. Usando fallback do .env: ' + str(destinatarios_lista)
            ))

        assunto = f"Controle Diário - {hoje.strftime('%d/%m/%Y')}"

        MESES_PT = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                     'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        
        # 6. Montagem do corpo em Texto Simples (Fallback)
        texto_simples = (
            f"Controle Diário do dia {hoje.day} de {MESES_PT[hoje.month - 1]} de {hoje.year}:\n\n"
            f"--- TOTAIS DO DIA ---\n"
            f"Atendimentos: {total_atendimento}\n"
            f"Inscrições Declaradas: {total_inscricoes}\n"
            f"Presentes nas Unidades: {total_presentes}\n"
            f"Ligações Recebidas: {total_recebidas}\n"
            f"Ligações Realizadas: {total_realizadas}\n\n"
            f"Verifique o e-mail em formato HTML para visualizar a tabela detalhada por escola."
        )

        # 7. Geração das tabelas HTML
        # Linhas da tabela de controles recebidos
        linhas_tabela = ""
        if controles_dia.exists():
            for c in controles_dia:
                usuario_nome = c.usuario.get_full_name() if c.usuario and c.usuario.get_full_name() else (c.usuario.username if c.usuario else "Sistema")
                tipo_badge = f'<span class="badge badge-uditech">UDITECH</span>' if c.escola.tipo == 'UDITECH' else f'<span class="badge badge-cp">CP</span>'
                
                linhas_tabela += f"""
                <tr>
                    <td><strong>{c.escola.nome}</strong><br>{tipo_badge}</td>
                    <td class="text-center">{c.atendimento}</td>
                    <td class="text-center">{c.inscricoes}</td>
                    <td class="text-center">{c.pessoas_presentes}</td>
                    <td class="text-center">{c.ligacoes_recebidas}</td>
                    <td class="text-center">{c.ligacoes_realizadas}</td>
                    <td><span class="user-pill">{usuario_nome}</span></td>
                </tr>
                """
        else:
            linhas_tabela = """
            <tr>
                <td colspan="7" class="text-center text-muted" style="padding: 30px 10px;">
                    Nenhum controle diário foi enviado pelas escolas até o momento hoje.
                </td>
            </tr>
            """

        # Lista de escolas pendentes
        escolas_pendentes_html = ""
        if escolas_pendentes.exists():
            for esc in escolas_pendentes:
                tipo_badge = f'<span class="badge badge-uditech">UDITECH</span>' if esc.tipo == 'UDITECH' else f'<span class="badge badge-cp">CP</span>'
                coordenador = esc.coordenador_user.get_full_name() if esc.coordenador_user else "Não atribuído"
                escolas_pendentes_html += f"""
                <li class="pendente-item">
                    <div>
                        <strong>{esc.nome}</strong> {tipo_badge}
                        <div class="coordenador-sub">Coord: {coordenador}</div>
                    </div>
                    <span class="status-warning">Pendente</span>
                </li>
                """
        else:
            escolas_pendentes_html = """
            <li class="pendente-item text-center text-success" style="justify-content: center; padding: 15px 0;">
                🎉 Todas as escolas enviaram o controle diário de hoje!
            </li>
            """

        # 8. Corpo do e-mail (HTML Premium)
        html_content = f"""
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
                    margin-bottom: 30px;
                    border-spacing: 10px 0;
                }}
                .kpi-card {{
                    display: table-cell;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                    padding: 15px 10px;
                    text-align: center;
                    vertical-align: middle;
                }}
                .kpi-title {{
                    font-size: 11px;
                    font-weight: 700;
                    text-transform: uppercase;
                    color: #64748b;
                    margin-bottom: 5px;
                }}
                .kpi-val {{
                    font-size: 22px;
                    font-weight: 800;
                    color: #1e3a8a;
                }}

                /* Tabela estilizada */
                .table-responsive {{
                    width: 100%;
                    overflow-x: auto;
                    margin-bottom: 35px;
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
                    padding: 12px 14px;
                    border-bottom: 2px solid #e5e7eb;
                    text-transform: uppercase;
                    font-size: 11px;
                }}
                td {{
                    padding: 14px;
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
                    font-size: 12px;
                    font-weight: 500;
                }}
                
                /* Seção de pendências */
                .section-title {{
                    font-size: 16px;
                    font-weight: 700;
                    color: #0f172a;
                    margin-top: 0;
                    margin-bottom: 15px;
                    border-left: 4px solid #ef4444;
                    padding-left: 10px;
                }}
                .section-title.success-line {{
                    border-left-color: #10b981;
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
                    padding: 12px 18px;
                    border-bottom: 1px solid #f0f2f5;
                }}
                .pendente-item:last-child {{
                    border-bottom: none;
                }}
                .coordenador-sub {{
                    font-size: 12px;
                    color: #64748b;
                    margin-top: 2px;
                }}
                .status-warning {{
                    font-size: 11px;
                    font-weight: 700;
                    color: #b91c1c;
                    background-color: #fef2f2;
                    padding: 4px 10px;
                    border-radius: 100px;
                }}
                
                /* Auditoria comparativa */
                .audit-box {{
                    background-color: #ecfdf5;
                    border: 1px solid #a7f3d0;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 35px;
                }}
                .audit-box h3 {{
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    color: #065f46;
                    font-weight: 700;
                    text-transform: uppercase;
                }}
                .audit-grid {{
                    display: table;
                    width: 100%;
                }}
                .audit-item {{
                    display: table-cell;
                    width: 50%;
                }}
                .audit-label {{
                    font-size: 13px;
                    color: #047857;
                }}
                .audit-value {{
                    font-size: 18px;
                    font-weight: 800;
                    color: #065f46;
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
                            Boa tarde, <strong>[[DEST_NOME]]</strong><br>
                            Segue o relatório de controle diário dos Centros Profissionalizantes e Uditechs
                        </p>
                        
                        <!-- KPIs Consolidadores do dia -->
                        <div class="kpi-container">
                            <div class="kpi-card">
                                <div class="kpi-title">Atendimentos</div>
                                <div class="kpi-val">{total_atendimento}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-title">Inscrições</div>
                                <div class="kpi-val">{total_inscricoes}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-title">Presentes</div>
                                <div class="kpi-val">{total_presentes}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-title">Ligs. Recebidas</div>
                                <div class="kpi-val">{total_recebidas}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-title">Ligs. Realizadas</div>
                                <div class="kpi-val">{total_realizadas}</div>
                            </div>
                        </div>



                        <!-- Tabela Detalhada -->
                        <h2 class="section-title success-line" style="border-left-color: #1e3a8a;">Tabela Detalhada por Unidade</h2>
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
                                    {linhas_tabela}
                                    
                                    <!-- Linha de Totais -->
                                    <tr class="total-row">
                                        <td>TOTAL DO DIA</td>
                                        <td class="text-center">{total_atendimento}</td>
                                        <td class="text-center">{total_inscricoes}</td>
                                        <td class="text-center">{total_presentes}</td>
                                        <td class="text-center">{total_recebidas}</td>
                                        <td class="text-center">{total_realizadas}</td>
                                        <td>-</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <!-- Seção de Pendências -->
                        <h2 class="section-title">Pendências de Envio</h2>
                        <ul class="pendentes-list">
                            {escolas_pendentes_html}
                        </ul>

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

        # 9. Envio Real do E-mail (Individual para personalização)
        from_email_config = getattr(settings, 'DEFAULT_FROM_EMAIL', 'sistema@gestaoqualificacao.com.br')
        
        sucessos = []
        for dest in destinatarios_lista:
            nome_dest = dest.get('nome', 'Equipe')
            email_dest = dest.get('email')
            
            # Substituir o placeholder pelo nome real do destinatário
            html_personalizado = html_content.replace('[[DEST_NOME]]', nome_dest)
            
            try:
                msg = EmailMultiAlternatives(
                    subject=assunto,
                    body=texto_simples,
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
