import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import gradio as gr
from pathlib import Path

# Importa componentes da UI
from ui.dashboard import Dashboard
from ui.email_form import EmailForm
from ui.contract_form import ContractForm

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main_app")

class MainApplication:
    """
    Classe principal que integra todos os componentes da interface de usuário.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa a aplicação principal.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        self.config_path = config_path
        
        # Inicializa componentes
        self.dashboard = Dashboard(config_path)
        self.email_form = EmailForm(config_path)
        self.contract_form = ContractForm(config_path)
    
    def launch(self, share: bool = False) -> None:
        """
        Inicia a aplicação principal.
        
        Args:
            share: Se deve compartilhar a aplicação publicamente
        """
        # Cria interface
        with gr.Blocks(title="Sistema de Gerenciamento de Contratos Escolares", theme="default") as interface:
            gr.Markdown("# Sistema de Gerenciamento de Contratos Escolares")
            
            with gr.Tabs():
                with gr.TabItem("Dashboard"):
                    # Incorpora dashboard
                    self.dashboard._update_dashboard()
                
                with gr.TabItem("Processamento de E-mails"):
                    # Incorpora formulário de e-mail
                    self.email_form.launch()
                
                with gr.TabItem("Gerenciamento de Contratos"):
                    # Incorpora formulário de contratos
                    self.contract_form.launch()
        
        # Inicia interface
        interface.launch(share=share)

# Exemplo de uso
if __name__ == "__main__":
    # Cria aplicação
    app = MainApplication()
    
    # Inicia aplicação
    app.launch()
