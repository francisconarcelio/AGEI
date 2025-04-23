import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
import datetime
import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard")

class Dashboard:
    """
    Classe responsável pela interface de usuário do sistema de gerenciamento de contratos.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o dashboard.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Configuração do dashboard
        self.dashboard_config = self.config.get('dashboard', {})
        
        # Caminhos para históricos
        self.routing_history_path = self.config.get('router', {}).get('routing_history_path', 'routing_history.json')
        self.notification_history_path = self.config.get('notification', {}).get('history_path', 'notification_history.json')
        
        # Inicializa interface
        self.interface = None
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do dashboard.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Dict[str, Any]: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'dashboard': {
                'title': 'Sistema de Gerenciamento de Contratos Escolares',
                'theme': 'default',
                'refresh_interval': 60,  # segundos
                'max_items_per_page': 20,
                'charts': {
                    'show_category_distribution': True,
                    'show_priority_distribution': True,
                    'show_department_distribution': True,
                    'show_routing_timeline': True
                }
            },
            'router': {
                'routing_history_path': 'routing_history.json'
            },
            'notification': {
                'history_path': 'notification_history.json'
            }
        }
        
        # Se não houver caminho de configuração, retorna configuração padrão
        if not config_path:
            logger.warning("Nenhum arquivo de configuração fornecido, usando configuração padrão")
            return default_config
        
        try:
            # Carrega configuração do arquivo
            with open(config_path, 'r') as file:
                config = json.load(file)
            
            logger.info(f"Configuração carregada de {config_path}")
            
            # Mescla com configuração padrão para garantir que todos os campos existam
            for section, values in default_config.items():
                if section not in config:
                    config[section] = values
                else:
                    if isinstance(values, dict):
                        for key, value in values.items():
                            if key not in config[section]:
                                config[section][key] = value
            
            return config
        
        except Exception as e:
            logger.error(f"Erro ao carregar configuração de {config_path}: {str(e)}")
            logger.warning("Usando configuração padrão")
            return default_config
    
    def _load_routing_history(self) -> List[Dict[str, Any]]:
        """
        Carrega histórico de encaminhamentos.
        
        Returns:
            List[Dict[str, Any]]: Histórico de encaminhamentos
        """
        try:
            if not os.path.exists(self.routing_history_path):
                logger.warning(f"Arquivo de histórico de encaminhamentos não encontrado: {self.routing_history_path}")
                return []
            
            with open(self.routing_history_path, 'r') as f:
                history = json.load(f)
            
            return history
        
        except Exception as e:
            logger.error(f"Erro ao carregar histórico de encaminhamentos: {str(e)}")
            return []
    
    def _load_notification_history(self) -> List[Dict[str, Any]]:
        """
        Carrega histórico de notificações.
        
        Returns:
            List[Dict[str, Any]]: Histórico de notificações
        """
        try:
            if not os.path.exists(self.notification_history_path):
                logger.warning(f"Arquivo de histórico de notificações não encontrado: {self.notification_history_path}")
                return []
            
            with open(self.notification_history_path, 'r') as f:
                history = json.load(f)
            
            return history
        
        except Exception as e:
            logger.error(f"Erro ao carregar histórico de notificações: {str(e)}")
            return []
    
    def _create_routing_dataframe(self) -> pd.DataFrame:
        """
        Cria DataFrame com histórico de encaminhamentos.
        
        Returns:
            pd.DataFrame: DataFrame com histórico de encaminhamentos
        """
        history = self._load_routing_history()
        
        if not history:
            return pd.DataFrame(columns=[
                'email_id', 'subject', 'from', 'category', 'priority', 
                'department', 'routing_status', 'routing_date', 'routed_to_email'
            ])
        
        df = pd.DataFrame(history)
        
        # Converte datas
        if 'routing_date' in df.columns:
            df['routing_date'] = pd.to_datetime(df['routing_date'])
        
        return df
    
    def _create_notification_dataframe(self) -> pd.DataFrame:
        """
        Cria DataFrame com histórico de notificações.
        
        Returns:
            pd.DataFrame: DataFrame com histórico de notificações
        """
        history = self._load_notification_history()
        
        if not history:
            return pd.DataFrame(columns=[
                'id', 'title', 'message', 'level', 'department', 'date'
            ])
        
        df = pd.DataFrame(history)
        
        # Converte datas
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def _create_category_chart(self, df: pd.DataFrame) -> Any:
        """
        Cria gráfico de distribuição de categorias.
        
        Args:
            df: DataFrame com histórico de encaminhamentos
            
        Returns:
            Any: Figura do matplotlib
        """
        try:
            if 'category' not in df.columns or df.empty:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.text(0.5, 0.5, "Sem dados disponíveis", ha='center', va='center', fontsize=12)
                ax.axis('off')
                return fig
            
            # Conta ocorrências de cada categoria
            category_counts = df['category'].value_counts()
            
            # Cria gráfico
            fig, ax = plt.subplots(figsize=(8, 6))
            category_counts.plot(kind='bar', ax=ax)
            
            ax.set_title('Distribuição de Categorias de E-mails')
            ax.set_xlabel('Categoria')
            ax.set_ylabel('Quantidade')
            ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            return fig
        
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de categorias: {str(e)}")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, f"Erro ao criar gráfico: {str(e)}", ha='center', va='center', fontsize=12)
            ax.axis('off')
            return fig
    
    def _create_priority_chart(self, df: pd.DataFrame) -> Any:
        """
        Cria gráfico de distribuição de prioridades.
        
        Args:
            df: DataFrame com histórico de encaminhamentos
            
        Returns:
            Any: Figura do matplotlib
        """
        try:
            if 'priority' not in df.columns or df.empty:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.text(0.5, 0.5, "Sem dados disponíveis", ha='center', va='center', fontsize=12)
                ax.axis('off')
                return fig
            
            # Conta ocorrências de cada prioridade
            priority_counts = df['priority'].value_counts()
            
            # Define ordem das prioridades
            priority_order = ['baixa', 'normal', 'alta', 'urgente']
            priority_counts = priority_counts.reindex(priority_order, fill_value=0)
            
            # Define cores para cada prioridade
            colors = ['green', 'blue', 'orange', 'red']
            
            # Cria gráfico
            fig, ax = plt.subplots(figsize=(8, 6))
            priority_counts.plot(kind='bar', ax=ax, color=colors)
            
            ax.set_title('Distribuição de Prioridades de E-mails')
            ax.set_xlabel('Prioridade')
            ax.set_ylabel('Quantidade')
            
            plt.tight_layout()
            
            return fig
        
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de prioridades: {str(e)}")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, f"Erro ao criar gráfico: {str(e)}", ha='center', va='center', fontsize=12)
            ax.axis('off')
            return fig
    
    def _create_department_chart(self, df: pd.DataFrame) -> Any:
        """
        Cria gráfico de distribuição de departamentos.
        
        Args:
            df: DataFrame com histórico de encaminhamentos
            
        Returns:
            Any: Figura do matplotlib
        """
        try:
            if 'department' not in df.columns or df.empty:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.text(0.5, 0.5, "Sem dados disponíveis", ha='center', va='center', fontsize=12)
                ax.axis('off')
                return fig
            
            # Conta ocorrências de cada departamento
            department_counts = df['department'].value_counts()
            
            # Cria gráfico
            fig, ax = plt.subplots(figsize=(8, 6))
            department_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%')
            
            ax.set_title('Distribuição de E-mails por Departamento')
            ax.set_ylabel('')
            
            plt.tight_layout()
            
            return fig
        
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de departamentos: {str(e)}")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, f"Erro ao criar gráfico: {str(e)}", ha='center', va='center', fontsize=12)
            ax.axis('off')
            return fig
    
    def _create_timeline_chart(self, df: pd.DataFrame) -> Any:
        """
        Cria gráfico de linha do tempo de encaminhamentos.
        
        Args:
            df: DataFrame com histórico de encaminhamentos
            
        Returns:
            Any: Figura do matplotlib
        """
        try:
            if 'routing_date' not in df.columns or df.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, "Sem dados disponíveis", ha='center', va='center', fontsize=12)
                ax.axis('off')
                return fig
            
            # Agrupa por data
            df['date'] = df['routing_date'].dt.date
            daily_counts = df.groupby('date').size()
            
            # Cria gráfico
            fig, ax = plt.subplots(figsize=(10, 6))
            daily_counts.plot(kind='line', ax=ax, marker='o')
            
            ax.set_title('Encaminhamentos por Dia')
            ax.set_xlabel('Data')
            ax.set_ylabel('Quantidade')
            
            plt.tight_layout()
            
            return fig
        
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de linha do tempo: {str(e)}")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f"Erro ao criar gráfico: {str(e)}", ha='center', va='center', fontsize=12)
            ax.axis('off')
            return fig
    
    def _create_routing_table(self, df: pd.DataFrame, max_rows: int = 20) -> str:
        """
        Cria tabela HTML com histórico de encaminhamentos.
        
        Args:
            df: DataFrame com histórico de encaminhamentos
            max_rows: Número máximo de linhas
            
        Returns:
            str: Tabela HTML
        """
        try:
            if df.empty:
                return "<p>Sem dados disponíveis</p>"
            
            # Ordena por data (mais recentes primeiro)
            if 'routing_date' in df.columns:
                df = df.sort_values('routing_date', ascending=False)
            
            # Limita número de linhas
            df = df.head(max_rows)
            
            # Seleciona colunas relevantes
            columns = ['subject', 'from', 'category', 'priority', 'department', 'routing_date']
            df_display = df[columns].copy()
            
            # Formata datas
            if 'routing_date' in df_display.columns:
                df_display['routing_date'] = df_display['routing_date'].dt.strftime('%d/%m/%Y %H:%M')
            
            # Renomeia colunas
            df_display.columns = ['Assunto', 'De', 'Categoria', 'Prioridade', 'Departamento', 'Data']
            
            # Converte para HTML
            html = df_display.to_html(classes='table table-striped', index=False)
            
            return html
        
        except Exception as e:
            logger.error(f"Erro ao criar tabela de encaminhamentos: {str(e)}")
            return f"<p>Erro ao criar tabela: {str(e)}</p>"
    
    def _create_notification_table(self, df: pd.DataFrame, max_rows: int = 20) -> str:
        """
        Cria tabela HTML com histórico de notificações.
        
        Args:
            df: DataFrame com histórico de notificações
            max_rows: Número máximo de linhas
            
        Returns:
            str: Tabela HTML
        """
        try:
            if df.empty:
                return "<p>Sem dados disponíveis</p>"
            
            # Ordena por data (mais recentes primeiro)
            if 'date' in df.columns:
                df = df.sort_values('date', ascending=False)
            
            # Limita número de linhas
            df = df.head(max_rows)
            
            # Seleciona colunas relevantes
            columns = ['title', 'level', 'department', 'date']
            df_display = df[columns].copy()
            
            # Formata datas
            if 'date' in df_display.columns:
                df_display['date'] = df_display['date'].dt.strftime('%d/%m/%Y %H:%M')
            
            # Renomeia colunas
            df_display.columns = ['Título', 'Nível', 'Departamento', 'Data']
            
            # Converte para HTML
            html = df_display.to_html(classes='table table-striped', index=False)
            
            return html
        
        except Exception as e:
            logger.error(f"Erro ao criar tabela de notificações: {str(e)}")
            return f"<p>Erro ao criar tabela: {str(e)}</p>"
    
    def _update_dashboard(self) -> Tuple[Any, Any, Any, Any, str, str]:
        """
        Atualiza o dashboard.
        
        Returns:
            Tuple: Gráficos e tabelas atualizados
        """
        # Carrega dados
        routing_df = self._create_routing_dataframe()
        notification_df = self._create_notification_dataframe()
        
        # Cria gráficos
        category_chart = self._create_category_chart(routing_df)
        priority_chart = self._create_priority_chart(routing_df)
        department_chart = self._create_department_chart(routing_df)
        timeline_chart = self._create_timeline_chart(routing_df)
        
        # Cria tabelas
        max_items = self.dashboard_config.get('max_items_per_page', 20)
        routing_table = self._create_routing_table(routing_df, max_items)
        notification_table = self._create_notification_table(notification_df, max_items)
        
        return (
            category_chart,
            priority_chart,
            department_chart,
            timeline_chart,
            routing_table,
            notification_table
        )
    
    def launch(self, share: bool = False) -> None:
        """
        Inicia o dashboard.
        
        Args:
            share: Se deve compartilhar o dashboard publicamente
        """
        # Título do dashboard
        title = self.dashboard_config.get('title', 'Sistema de Gerenciamento de Contratos Escolares')
        
        # Tema
        theme = self.dashboard_config.get('theme', 'default')
        
        # Intervalo de atualização
        refresh_interval = self.dashboard_config.get('refresh_interval', 60)
        
        # Configuração de gráficos
        charts_config = self.dashboard_config.get('charts', {})
        
        # Cria interface
        with gr.Blocks(title=title, theme=theme) as interface:
            gr.Markdown(f"# {title}")
            
            with gr.Tabs():
                with gr.TabItem("Dashboard"):
                    gr.Markdown("## Visão Geral")
                    
                    with gr.Row():
                        with gr.Column():
                            if charts_config.get('show_category_distribution', True):
                                category_chart = gr.Plot(label="Distribuição de Categorias")
                        
                        with gr.Column():
                            if charts_config.get('show_priority_distribution', True):
                                priority_chart = gr.Plot(label="Distribuição de Prioridades")
                    
                    with gr.Row():
                        with gr.Column():
                            if charts_config.get('show_department_distribution', True):
                                department_chart = gr.Plot(label="Distribuição por Departamento")
                        
                        with gr.Column():
                            if charts_config.get('show_routing_timeline', True):
                                timeline_chart = gr.Plot(label="Encaminhamentos por Dia")
                    
                    refresh_button = gr.Button("Atualizar Dashboard")
                
                with gr.TabItem("Encaminhamentos"):
                    gr.Markdown("## Histórico de Encaminhamentos")
                    routing_table = gr.HTML()
                
                with gr.TabItem("Notificações"):
                    gr.Markdown("## Histórico de Notificações")
                    notification_table = gr.HTML()
            
            # Função de atualização
            def update_func():
                return self._update_dashboard()
            
            # Configura atualização
            refresh_button.click(
                fn=update_func,
                outputs=[
                    category_chart,
                    priority_chart,
                    department_chart,
                    timeline_chart,
                    routing_table,
                    notification_table
                ]
            )
            
            # Atualização automática
            interface.load(
                fn=update_func,
                outputs=[
                    category_chart,
                    priority_chart,
                    department_chart,
                    timeline_chart,
                    routing_table,
                    notification_table
                ]
            )
            
            # Configura atualização periódica
            if refresh_interval > 0:
                interface.load(
                    fn=update_func,
                    outputs=[
                        category_chart,
                        priority_chart,
                        department_chart,
                        timeline_chart,
                        routing_table,
                        notification_table
                    ],
                    every=refresh_interval
                )
        
        # Salva referência à interface
        self.interface = interface
        
        # Inicia interface
        interface.launch(share=share)

# Exemplo de uso
if __name__ == "__main__":
    # Cria dashboard
    dashboard = Dashboard()
    
    # Inicia dashboard
    dashboard.launch()
