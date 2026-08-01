import os

from django.core.exceptions import ValidationError

# Extensoes aceitas para documentos de aluno e da unidade (identidade, comprovantes,
# atestados, planilhas, etc). Nenhum tipo executavel (.exe, .php, .html, .svg, .js...).
ALLOWED_UPLOAD_EXTENSIONS = [
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.doc', '.docx', '.xls', '.xlsx',
]

MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


def validate_upload_file(f):
    """
    Validador reutilizavel para uploads de documentos (ArquivoAluno, DocumentoUnidade).
    Antes disso, qualquer usuario autenticado com acesso de staff podia enviar
    qualquer extensao (.exe, .html, .svg) e qualquer tamanho de arquivo.
    """
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f"Tipo de arquivo não permitido ({ext or 'sem extensão'}). "
            f"Extensões aceitas: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}."
        )
    if f.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            f"Arquivo muito grande ({f.size / (1024 * 1024):.1f} MB). "
            f"Máximo permitido: {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
        )
