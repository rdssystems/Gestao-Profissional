from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Count, Q, Prefetch
from .models import VideoTreinamento, ProgressoTreinamento

class TreinamentoListView(LoginRequiredMixin, ListView):
    model = VideoTreinamento
    template_name = 'treinamento/treinamento_list.html'
    context_object_name = 'videos'

    def get_queryset(self):
        return VideoTreinamento.objects.filter(ativo=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Obter IDs dos vídeos concluídos pelo usuário atual
        concluidos = ProgressoTreinamento.objects.filter(
            usuario=user, concluido=True
        ).values_list('video_id', flat=True)
        context['concluidos_ids'] = list(concluidos)
        
        # Calcular porcentagem de conclusão
        total = context['videos'].count()
        if total > 0:
            concluidos_count = len(concluidos)
            context['progresso_geral'] = int((concluidos_count / total) * 100)
        else:
            context['progresso_geral'] = 0
            
        return context

class TreinamentoDetailView(LoginRequiredMixin, DetailView):
    model = VideoTreinamento
    template_name = 'treinamento/treinamento_detail.html'
    context_object_name = 'video'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        progresso = ProgressoTreinamento.objects.filter(usuario=user, video=self.object).first()
        context['concluido'] = progresso.concluido if progresso else False
        
        # Lista lateral de vídeos para navegação rápida
        context['playlists'] = VideoTreinamento.objects.filter(ativo=True).only('id', 'titulo', 'ordem')
        
        # Obter IDs concluídos para marcar na playlist
        concluidos = ProgressoTreinamento.objects.filter(
            usuario=user, concluido=True
        ).values_list('video_id', flat=True)
        context['concluidos_ids'] = list(concluidos)

        return context

class MarcarConcluidoAjaxView(LoginRequiredMixin, View):
    def post(self, request, pk):
        video = get_object_or_404(VideoTreinamento, pk=pk)
        progresso, created = ProgressoTreinamento.objects.get_or_create(
            usuario=request.user, 
            video=video
        )
        # O usuário pediu para que não seja possível desmarcar a conclusão.
        # Uma vez concluído, fica concluído permanentemente.
        progresso.concluido = True
        progresso.save()
        
        return JsonResponse({
            'status': 'success', 
            'concluido': progresso.concluido,
            'mensagem': 'Progresso atualizado!'
        })

class RelatorioTreinamentoView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Visão administrativa para ver quem assistiu o quê."""
    model = User
    template_name = 'treinamento/relatorio_treinamento.html'
    context_object_name = 'usuarios'

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        # Prefetch progressos para evitar queries N+1
        return User.objects.filter(is_active=True).prefetch_related(
            Prefetch('progressos_treinamento', queryset=ProgressoTreinamento.objects.filter(concluido=True))
        ).order_by('username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        videos = VideoTreinamento.objects.filter(ativo=True)
        context['videos_treinamento'] = videos
        context['total_videos'] = videos.count()
        return context
