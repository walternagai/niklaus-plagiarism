"""
Results tab for Niklaus UI.
"""

import streamlit as st
from typing import Dict, Any, List
from ui.components.tables import display_similarity_table
from ui.components.exporter import export_results, generate_summary_report


def render_results_tab(results: Dict[str, Any], settings: Dict[str, Any]) -> None:
    """
    Display results tab.
    
    Args:
        results: Analysis results
        settings: User settings
    """
    st.markdown("### :bar_chart: Resultados da Análise")
    
    if not results.get('suspicious_pairs'):
        st.success("✅ Não foram encontrados trechos de código plagiados abaixo do limite definido.")
        return
    
    # Summary stats
    from ui.components.exporter import display_summary_stats
    display_summary_stats(results)
    
    # Help expander
    with st.expander("❓ Como interpretar os resultados?"):
        st.markdown(get_help_message("interpret_similarity"))
    
    st.markdown("---")
    
    # Display suspicious pairs table
    filtered_df = display_similarity_table(results['suspicious_pairs'], results['threshold'])
    
    # AI Analysis (if available)
    if results.get('ai_analyses') and filtered_df is not None and len(filtered_df) > 0:
        st.markdown("### :notebook: Análises com IA")
        
        for idx, row in filtered_df.iterrows():
            file1 = row['Arquivo 1']
            file2 = row['Arquivo 2']
            sim = row['Similaridade']
            key = f"{file1}_{file2}"
            
            if key in results['ai_analyses']:
                with st.expander(f":mag_right: {file1} ↔ {file2} - {sim:.1%}"):
                    # Stream the AI response
                    analysis = results['ai_analyses'][key]
                    _stream_ai_response(analysis)
                    
                    # Show code comparison
                    if st.checkbox("Ver código", key=f"show_code_{idx}"):
                        _show_code_comparison(results, file1, file2)
    
    # Export options
    export_results(results, results['suspicious_pairs'], settings)


def _stream_ai_response(analysis: str) -> None:
    """Stream AI response word by word."""
    import time
    
    placeholder = st.empty()
    words = analysis.split()
    
    for i, word in enumerate(words):
        partial = ' '.join(words[:i+1])
        placeholder.markdown(partial + "▌")
        time.sleep(0.01)
    
    placeholder.markdown(analysis)


def _show_code_comparison(results: Dict[str, Any], file1: str, file2: str) -> None:
    """Show side-by-side code comparison."""
    try:
        idx1 = results['files'].index(file1)
        idx2 = results['files'].index(file2)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**{file1}**")
            st.code(results['files_content'][idx1], language=results['language'].lower())
        
        with col2:
            st.markdown(f"**{file2}**")
            st.code(results['files_content'][idx2], language=results['language'].lower())
    
    except (ValueError, KeyError) as e:
        st.warning("Código não disponível para comparação.")