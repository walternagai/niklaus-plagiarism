"""
Export components for Niklaus UI.
"""

import json
from datetime import datetime
from typing import Dict, List, Any
import streamlit as st
import pandas as pd


def export_results(
    results: Dict[str, Any],
    suspicious_pairs: List[tuple],
    settings: Dict[str, Any]
) -> None:
    """
    Display export buttons for results.
    
    Args:
        results: Analysis results
        suspicious_pairs: List of suspicious pairs
        settings: User settings
    """
    st.markdown("---")
    st.markdown("### :inbox_tray: Exportar Resultados")
    
    col1, col2, col3 = st.columns(3)
    
    # CSV Export
    with col1:
        _export_csv(suspicious_pairs)
    
    # JSON Export
    with col2:
        _export_json(results, suspicious_pairs, settings)
    
    # PDF Export
    with col3:
        _export_pdf_button(results, settings)


def _export_csv(suspicious_pairs: List[tuple]) -> None:
    """Export results to CSV."""
    if not suspicious_pairs:
        st.button("📥 Baixar CSV", use_container_width=True, disabled=True)
        return
    
    df_data = [
        {'Arquivo 1': f1, 'Arquivo 2': f2, 'Similaridade': sim}
        for f1, f2, sim in suspicious_pairs
    ]
    df = pd.DataFrame(df_data)
    csv = df.to_csv(index=False)
    
    st.download_button(
        "📥 Baixar CSV",
        data=csv,
        file_name=f"similaridade_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def _export_json(results: Dict[str, Any], suspicious_pairs: List[tuple], settings: Dict[str, Any]) -> None:
    """Export results to JSON."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "language": results['language'],
        "threshold": results['threshold'],
        "files": results['files'],
        "analysis_time": results['analysis_time'],
        "suspicious_pairs": [
            {"file1": f1, "file2": f2, "similarity": float(sim)}
            for f1, f2, sim in suspicious_pairs
        ],
        "settings": {
            "max_workers": settings.get('max_workers'),
            "use_cache": settings.get('use_cache'),
            "enable_ai": settings.get('enable_ai')
        }
    }
    
    st.download_button(
        "📥 Baixar JSON",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name=f"relatorio_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True
    )


def _export_pdf_button(results: Dict[str, Any], settings: Dict[str, Any]) -> None:
    """Display PDF export button (not yet implemented)."""
    st.button(
        "📥 Baixar PDF",
        use_container_width=True,
        disabled=True,
        help="Exportação PDF em desenvolvimento. Use CSV ou JSON por enquanto.",
    )


def generate_summary_report(results: Dict[str, Any], settings: Dict[str, Any]) -> str:
    """
    Generate a text summary report.
    
    Args:
        results: Analysis results
        settings: User settings
    
    Returns:
        Summary text
    """
    summary = f"""
RELATÓRIO DE ANÁLISE DE PLÁGIO - NIKLAUS
{'=' * 50}

Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

CONFIGURAÇÕES
--------------
Linguagem: {results['language']}
Limite de Similaridade: {results['threshold']:.0%}
Workers Paralelos: {settings['max_workers']}
Cache: {'Ativado' if settings['use_cache'] else 'Desativado'}
Análise com IA: {'Ativada' if settings['enable_ai'] else 'Desativada'}

RESULTADOS
----------
Arquivos Analisados: {len(results['files'])}
Comparações Realizadas: {len(results['textual_similarities'])}
Pares Suspeitos: {len(results['suspicious_pairs'])}
Tempo de Análise: {results['analysis_time']:.2f}s

"""
    
    if results['suspicious_pairs']:
        summary += "\nPARES COM ALTA SIMILARIDADE\n"
        summary += "-" * 50 + "\n"
        summary += f"{'Arquivo 1':<30} {'Arquivo 2':<30} {'Similaridade':>12}\n"
        summary += "-" * 72 + "\n"
        
        for f1, f2, sim in sorted(results['suspicious_pairs'], key=lambda x: x[2], reverse=True)[:20]:
            summary += f"{f1[:28]:<30} {f2[:28]:<30} {sim:>11.1%}\n"
        
        if len(results['suspicious_pairs']) > 20:
            summary += f"\n... e mais {len(results['suspicious_pairs']) - 20} pares\n"
    
    return summary


def display_summary_stats(results: Dict[str, Any]) -> None:
    """
    Display summary statistics.
    
    Args:
        results: Analysis results
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Arquivos Analisados", len(results['files']))
    
    with col2:
        st.metric("Pares Suspeitos", len(results['suspicious_pairs']))
    
    with col3:
        if results['suspicious_pairs']:
            max_sim = max(s[2] for s in results['suspicious_pairs'])
            st.metric("Maior Similaridade", f"{max_sim:.1%}")
        else:
            st.metric("Maior Similaridade", "N/A")
    
    with col4:
        st.metric("Tempo de Análise", f"{results['analysis_time']:.2f}s")