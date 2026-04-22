import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestao_qualificacao_profissional.settings")
django.setup()

from django.utils import timezone
from cursos.models import Inscricao
from core.models import AuditLog
from django.contrib.contenttypes.models import ContentType

def run():
    print("Iniciando backfill de datas de conclusão e desistência...")
    inscricoes = Inscricao.objects.filter(status__in=['concluido', 'desistente'])
    ct = ContentType.objects.get_for_model(Inscricao)
    
    count = 0
    fallback = 0
    
    for inscricao in inscricoes:
        # Procurar no AuditLog por mudanças de status
        logs = AuditLog.objects.filter(content_type=ct, object_id=str(inscricao.id)).order_by('-data_hora')
        
        updated = False
        for log in logs:
            try:
                detalhes = json.loads(log.detalhes)
                if 'alteracoes' in detalhes and 'status' in detalhes['alteracoes']:
                    if detalhes['alteracoes']['status'] == inscricao.status:
                        # Encontramos o log correspondente
                        if inscricao.status == 'concluido' and not inscricao.data_conclusao:
                            Inscricao.objects.filter(id=inscricao.id).update(data_conclusao=log.data_hora)
                            updated = True
                        elif inscricao.status == 'desistente' and not inscricao.data_desistencia:
                            Inscricao.objects.filter(id=inscricao.id).update(data_desistencia=log.data_hora)
                            updated = True
                        break 
            except Exception:
                continue
                
        # Se não tiver log antigo, usa o dia atual
        if not updated:
            if inscricao.status == 'concluido' and not inscricao.data_conclusao:
                Inscricao.objects.filter(id=inscricao.id).update(data_conclusao=timezone.now())
                fallback += 1
            elif inscricao.status == 'desistente' and not inscricao.data_desistencia:
                Inscricao.objects.filter(id=inscricao.id).update(data_desistencia=timezone.now())
                fallback += 1
        else:
            count += 1
            
    print(f"Backfill concluído! {count} logs encontrados e {fallback} sem log definidos para hoje.")

if __name__ == "__main__":
    run()
