from .curso import (
    TipoCursoForm,
    CursoListView,
    CursoDetailView,
    CursoCreateView,
    CursoUpdateView,
    CursoDeleteView,
    CursoStatusUpdateView,
    CursoConcluintesView,
    CursoConcluintesXLSXView,
    ExportarAlunosView,
    CursoImprimirListaView,
    TipoCursoListView,
    TipoCursoCreateView,
    TipoCursoUpdateView,
    TipoCursoDeleteView,
)
from .matricula import (
    InscricaoCreateView,
    UpdateInscricaoStatusView,
    MatriculaView,
    AtualizarContatoMatriculaAjaxView,
    MatricularAlunoDiretoView,
    CancelarMatriculaDiretoView,
    InscricaoDeleteView,
)
from .chamada import (
    ChamadaCursoListView,
    FazerChamadaView,
    ObterDadosChamadaDataView,
    HistoricoChamadasCursoView,
    RelatorioFrequenciaView,
    ExcluirRegistroAulaView,
    ChamadaPublicaView,
    RegenerarTokensView,
)
from .csv_import import (
    CursoCSVUploadView,
    DownloadCursoTemplateView,
)
from .parceiro_ementa import (
    ParceiroListView,
    ParceiroCreateView,
    ParceiroUpdateView,
    ParceiroDeleteView,
    EmentaPadraoListView,
    EmentaPadraoCreateView,
    EmentaPadraoUpdateView,
    EmentaPadraoDeleteView,
    ObterEmentaView,
)
from .avaliacao import (
    CursoAvaliacaoDashboardView,
    AvaliarProfessorAcessoView,
    AvaliarProfessorListaView,
    AvaliarEstudanteAjaxView,
    AvaliarCursoPublicView,
    ObterDadosGraficosAvaliacaoView,
    AvaliacaoDetalhesView,
    CursoAvaliacaoConsolidadoView,
    CursoQualitativosView,
)
