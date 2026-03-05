"""
Interactive tutorial/tour system for user onboarding.
Guides users through application features step by step.
"""

import streamlit as st
from typing import List, Dict, Any, Optional


class TutorialStep:
    """Represents a single tutorial step."""
    
    def __init__(
        self,
        step_id: str,
        title: str,
        description: str,
        target_element: str,
        position: str = "right",
        icon: str = "📌",
        action_hint: Optional[str] = None
    ):
        self.step_id = step_id
        self.title = title
        self.description = description
        self.target_element = target_element
        self.position = position
        self.icon = icon
        self.action_hint = action_hint


class TutorialManager:
    """Manages interactive tutorials with progress tracking."""
    
    def __init__(self):
        self.tutorials: Dict[str, List[TutorialStep]] = {}
        self._initialize_tutorials()
    
    def _initialize_tutorials(self):
        """Initialize default tutorials."""
        self.tutorials['getting_started'] = [
            TutorialStep(
                step_id='welcome',
                title='Bem-vindo ao Niklaus!',
                description='Este tutorial vai guiá-lo pelas principais funcionalidades do sistema.',
                target_element='main',
                position='center',
                icon='👋',
                action_hint='Clique em "Próximo" para continuar'
            ),
            TutorialStep(
                step_id='sidebar_config',
                title='Configuração da Sidebar',
                description='''
                Na sidebar à esquerda você encontra:
                - **Presets Rápidos**: Configurações pré-definidas para análise
                - **API**: Status da conexão com Maritaca AI
                - **Linguagem**: Selecione a linguagem dos arquivos
                - **Threshold**: Ajuste a sensibilidade da detecção
                - **Performance**: Configure workers e cache
                ''',
                target_element='sidebar',
                position='right',
                icon='⚙️',
                action_hint='Explore as opções na sidebar'
            ),
            TutorialStep(
                step_id='presets',
                title='Presets Rápidos',
                description='''
                Use os presets para configurações rápidas:
                
                **🚀 Rápido**: Análise básica sem IA
                - Threshold: 80%
                - Workers: 2
                - Ideal para: Verificação rápida
                
                **🔍 Completo**: Análise detalhada com IA
                - Threshold: 70%
                - Workers: 4
                - Ideal para: Análise profunda
                ''',
                target_element='sidebar',
                position='right',
                icon='⚡',
                action_hint='Clique em um preset para aplicá-lo'
            ),
            TutorialStep(
                step_id='upload_tab',
                title='Aba de Upload',
                description='''
                Na aba **Upload** você pode:
                - Fazer upload de arquivos ZIP
                - Configurar o nome da análise
                - Iniciar a análise
                - Cancelar análises em andamento
                ''',
                target_element='tabs',
                position='below',
                icon='📤',
                action_hint='Vá para a aba Upload para continuar'
            ),
            TutorialStep(
                step_id='results_tab',
                title='Aba de Resultados',
                description='''
                Na aba **Resultados** você encontra:
                - Lista de pares suspeitos
                - Similaridade entre arquivos
                - Detalhes de cada comparação
                - Opções de exportação
                ''',
                target_element='tabs',
                position='below',
                icon='📊',
                action_hint='Os resultados aparecem automaticamente após análise'
            ),
            TutorialStep(
                step_id='statistics_tab',
                title='Aba de Estatísticas',
                description='''
                Na aba **Estatísticas** você vê:
                - Média de similaridade
                - Máximo de similaridade
                - Distribuição de similaridades
                - Métricas detalhadas
                ''',
                target_element='tabs',
                position='below',
                icon='📈',
                action_hint='Explore as estatísticas após análise'
            ),
            TutorialStep(
                step_id='history_tab',
                title='Aba de Histórico',
                description='''
                Na aba **Histórico** você pode:
                - Ver todas as análises anteriores
                - Filtrar por data/status
                - Carregar análises antigas
                - Exportar ou excluir análises
                ''',
                target_element='tabs',
                position='below',
                icon='📁',
                action_hint='Acesse o histórico para revisar análises'
            ),
            TutorialStep(
                step_id='analysis_process',
                title='Processo de Análise',
                description='''
                O Niklaus realiza análises em etapas:
                
                1. **Extração**: Arquivos do ZIP
                2. **Similaridade Textual**: Comparação de código
                3. **AST**: Estrutura da árvore sintática
                4. **Métricas**: Complexidade, estilo
                5. **Clustering**: Agrupamento de arquivos
                6. **IA**: Análise avançada (opcional)
                ''',
                target_element='main',
                position='center',
                icon='🔬',
                action_hint='O progresso é mostrado em tempo real'
            ),
            TutorialStep(
                step_id='threshold_config',
                title='Configurando o Threshold',
                description='''
                O threshold controla a sensibilidade:
                
                - **🔴 Agressivo (50%)**: Detecta mais plágio, pode ter falsos positivos
                - **🟡 Moderado (70%)**: Equilibrado, recomendado
                - **🟢 Conservador (80%)**: Alta confiança, menos detecções
                
                Escolha baseado no contexto da análise.
                ''',
                target_element='sidebar',
                position='right',
                icon='🎯',
                action_hint='Ajuste o threshold na sidebar'
            ),
            TutorialStep(
                step_id='cache_feature',
                title='Cache de Análises',
                description='''
                O cache permite reutilizar resultados:
                
                - **Ativar**: Análises idênticas são recuperadas
                - **Estatísticas**: Veja tamanho e dados do cache
                - **Limpar**: Remova dados antigos do cache
                
                Útil para análises repetidas dos mesmos arquivos.
                ''',
                target_element='sidebar',
                position='right',
                icon='💾',
                action_hint='Ative o cache na sidebar'
            ),
            TutorialStep(
                step_id='ready',
                title='Pronto para Começar!',
                description='''
                Você está pronto para usar o Niklaus!
                
                **Próximos passos:**
                1. Configure a API na sidebar
                2. Selecione a linguagem
                3. Ajuste o threshold
                4. Faça upload do ZIP
                5. Inicie a análise
                
                **Dica**: Use presets para configurações rápidas
                ''',
                target_element='main',
                position='center',
                icon='✅',
                action_hint='Clique em "Concluir" para começar'
            )
        ]
        
        self.tutorials['advanced_features'] = [
            TutorialStep(
                step_id='advanced_intro',
                title='Recursos Avançados',
                description='Explore recursos avançados para análise profunda.',
                target_element='tabs',
                position='below',
                icon='🎓'
            ),
            TutorialStep(
                step_id='graph_tab',
                title='Grafo de Similaridades',
                description='''
                A aba **Graph** mostra:
                - Rede de conexões entre arquivos
                - Nós coloridos por similaridade
                - Arestas com peso de similaridade
                - Visualização interativa
                ''',
                target_element='tabs',
                position='below',
                icon='🕸️'
            ),
            TutorialStep(
                step_id='ast_analysis',
                title='Análise AST',
                description='''
                Na aba **Advanced**:
                - Análise de árvore sintática
                - Estrutura de código
                - Padrões estruturais
                - Métricas avançadas
                ''',
                target_element='tabs',
                position='below',
                icon='🌳'
            )
        ]
    
    def get_tutorial(self, tutorial_id: str) -> Optional[List[TutorialStep]]:
        """Get tutorial by ID."""
        return self.tutorials.get(tutorial_id)
    
    def get_tutorial_ids(self) -> List[str]:
        """Get all tutorial IDs."""
        return list(self.tutorials.keys())
    
    def get_step(self, tutorial_id: str, step_index: int) -> Optional[TutorialStep]:
        """Get specific step from tutorial."""
        tutorial = self.tutorials.get(tutorial_id)
        if tutorial and 0 <= step_index < len(tutorial):
            return tutorial[step_index]
        return None
    
    def get_next_step(self, tutorial_id: str, current_step: int) -> Optional[TutorialStep]:
        """Get next step in tutorial."""
        return self.get_step(tutorial_id, current_step + 1)
    
    def get_prev_step(self, tutorial_id: str, current_step: int) -> Optional[TutorialStep]:
        """Get previous step in tutorial."""
        if current_step > 0:
            return self.get_step(tutorial_id, current_step - 1)
        return None


_tutorial_manager: Optional[TutorialManager] = None


def get_tutorial_manager() -> TutorialManager:
    """Get global tutorial manager instance."""
    global _tutorial_manager
    if _tutorial_manager is None:
        _tutorial_manager = TutorialManager()
    return _tutorial_manager


def is_tutorial_completed(tutorial_id: str) -> bool:
    """Check if tutorial has been completed."""
    return st.session_state.get(f'tutorial_{tutorial_id}_completed', False)


def mark_tutorial_completed(tutorial_id: str):
    """Mark tutorial as completed."""
    st.session_state[f'tutorial_{tutorial_id}_completed'] = True


def get_tutorial_progress(tutorial_id: str) -> int:
    """Get current step in tutorial."""
    return st.session_state.get(f'tutorial_{tutorial_id}_step', 0)


def set_tutorial_progress(tutorial_id: str, step: int):
    """Set current step in tutorial."""
    st.session_state[f'tutorial_{tutorial_id}_step'] = step


def reset_tutorial(tutorial_id: str):
    """Reset tutorial progress."""
    st.session_state[f'tutorial_{tutorial_id}_step'] = 0
    st.session_state[f'tutorial_{tutorial_id}_completed'] = False


def should_show_tutorial(tutorial_id: str = 'getting_started') -> bool:
    """Check if tutorial should be shown."""
    return st.session_state.get('show_tutorial', False) and not is_tutorial_completed(tutorial_id)


def start_tutorial(tutorial_id: str = 'getting_started'):
    """Start tutorial."""
    st.session_state['show_tutorial'] = True
    st.session_state['current_tutorial'] = tutorial_id
    set_tutorial_progress(tutorial_id, 0)


def end_tutorial():
    """End tutorial."""
    current_tutorial = st.session_state.get('current_tutorial', 'getting_started')
    mark_tutorial_completed(current_tutorial)
    st.session_state['show_tutorial'] = False


def render_tutorial_step(tutorial_id: str = 'getting_started'):
    """Render current tutorial step."""
    manager = get_tutorial_manager()
    current_step_index = get_tutorial_progress(tutorial_id)
    step = manager.get_step(tutorial_id, current_step_index)
    
    if not step:
        return
    
    tutorial = manager.get_tutorial(tutorial_id)
    total_steps = len(tutorial) if tutorial else 0
    
    st.markdown("---")
    
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 10px;
    '>
        <h3 style='margin: 0; color: white;'>{step.icon} {step.title}</h3>
        <p style='margin: 5px 0 0 0; opacity: 0.9;'>Passo {current_step_index + 1} de {total_steps}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    '>
        {step.description}
    </div>
    """, unsafe_allow_html=True)
    
    if step.action_hint:
        st.info(f"💡 {step.action_hint}")
    
    progress = (current_step_index + 1) / total_steps if total_steps > 0 else 0
    st.progress(progress)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_step_index > 0:
            if st.button("⬅️ Anterior", use_container_width=True):
                set_tutorial_progress(tutorial_id, current_step_index - 1)
                st.rerun()
    
    with col2:
        if st.button("⏭️ Pular Tutorial", use_container_width=True, type="secondary"):
            end_tutorial()
            st.rerun()
    
    with col3:
        if current_step_index < total_steps - 1:
            if st.button("Próximo ➡️", use_container_width=True, type="primary"):
                set_tutorial_progress(tutorial_id, current_step_index + 1)
                st.rerun()
        else:
            if st.button("✅ Concluir", use_container_width=True, type="primary"):
                end_tutorial()
                st.rerun()


def render_tutorial_launcher():
    """Render tutorial launcher button."""
    if st.sidebar.button("📖 Tutorial", use_container_width=True):
        start_tutorial()
        st.rerun()
    
    if is_tutorial_completed('getting_started'):
        if st.sidebar.button("🔄 Repetir Tutorial", use_container_width=True):
            reset_tutorial('getting_started')
            start_tutorial()
            st.rerun()