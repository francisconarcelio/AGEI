import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import gradio as gr
from pathlib import Path
import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_form")

class EmailForm:
    """
    Classe responsável pela interface de formulário para envio e processamento manual de e-mails.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o formulário de e-mail.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Configuração do formulário
        self.form_config = self.config.get('form', {})
        
        # Inicializa interface
        self.interface = None
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do formulário.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Dict[str, Any]: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'form': {
                'title': 'Processamento Manual de E-mails',
                'theme': 'default',
                'categories': [
                    'novo_contrato',
                    'renovacao',
                    'alteracao',
                    'cancelamento',
                    'pagamento',
                    'duvida',
                    'reclamacao',
                    'suporte',
                    'outro'
                ],
                'priorities': [
                    'baixa',
                    'normal',
                    'alta',
                    'urgente'
                ],
                'departments': [
                    'comercial',
                    'juridico',
                    'financeiro',
                    'atendimento',
                    'suporte_tecnico',
                    'triagem'
                ]
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
    
    def _process_email(self, from_email: str, subject: str, body: str, 
                      category: str, priority: str, department: str, 
                      attachments: List[str]) -> Dict[str, Any]:
        """
        Processa um e-mail manualmente.
        
        Args:
            from_email: E-mail do remetente
            subject: Assunto do e-mail
            body: Corpo do e-mail
            category: Categoria do e-mail
            priority: Prioridade do e-mail
            department: Departamento de destino
            attachments: Lista de anexos
            
        Returns:
            Dict[str, Any]: Resultado do processamento
        """
        try:
            # Cria e-mail
            email = {
                'id': f"manual_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                'from': from_email,
                'subject': subject,
                'body': body,
                'date': datetime.datetime.now().isoformat(),
                'ml_category': category,
                'ml_category_confidence': 1.0,
                'ml_priority': priority,
                'ml_priority_confidence': 1.0,
                'department': department,
                'department_confidence': 1.0,
                'attachments': []
            }
            
            # Processa anexos
            for attachment_path in attachments:
                if attachment_path and os.path.exists(attachment_path):
                    filename = os.path.basename(attachment_path)
                    email['attachments'].append({
                        'filename': filename,
                        'path': attachment_path,
                        'content_type': self._guess_content_type(filename)
                    })
            
            # Aqui seria implementado o encaminhamento do e-mail
            # Como é apenas um exemplo, apenas logamos a ação
            logger.info(f"E-mail processado manualmente: {subject}")
            logger.info(f"Categoria: {category}, Prioridade: {priority}, Departamento: {department}")
            
            return {
                'success': True,
                'message': f"E-mail '{subject}' processado com sucesso e encaminhado para {department}",
                'email': email
            }
        
        except Exception as e:
            logger.error(f"Erro ao processar e-mail manualmente: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao processar e-mail: {str(e)}",
                'error': str(e)
            }
    
    def _guess_content_type(self, filename: str) -> str:
        """
        Adivinha o tipo de conteúdo de um arquivo.
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            str: Tipo de conteúdo
        """
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(filename)
        
        if not content_type:
            # Tenta adivinhar pelo sufixo
            suffix = os.path.splitext(filename)[1].lower()
            
            if suffix == '.pdf':
                content_type = 'application/pdf'
            elif suffix in ['.doc', '.docx']:
                content_type = 'application/msword'
            elif suffix in ['.xls', '.xlsx']:
                content_type = 'application/vnd.ms-excel'
            elif suffix == '.txt':
                content_type = 'text/plain'
            elif suffix in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif suffix == '.png':
                content_type = 'image/png'
            else:
                content_type = 'application/octet-stream'
        
        return content_type
    
    def launch(self, share: bool = False) -> None:
        """
        Inicia o formulário de e-mail.
        
        Args:
            share: Se deve compartilhar o formulário publicamente
        """
        # Título do formulário
        title = self.form_config.get('title', 'Processamento Manual de E-mails')
        
        # Tema
        theme = self.form_config.get('theme', 'default')
        
        # Opções de categoria, prioridade e departamento
        categories = self.form_config.get('categories', [])
        priorities = self.form_config.get('priorities', [])
        departments = self.form_config.get('departments', [])
        
        # Cria interface
        with gr.Blocks(title=title, theme=theme) as interface:
            gr.Markdown(f"# {title}")
            
            with gr.Row():
                with gr.Column():
                    from_email = gr.Textbox(label="E-mail do Remetente", placeholder="nome@exemplo.com")
                    subject = gr.Textbox(label="Assunto", placeholder="Assunto do e-mail")
                    body = gr.Textbox(label="Corpo do E-mail", placeholder="Conteúdo do e-mail", lines=10)
                    attachments = gr.File(label="Anexos", file_count="multiple")
                
                with gr.Column():
                    category = gr.Dropdown(label="Categoria", choices=categories, value=categories[0] if categories else None)
                    priority = gr.Dropdown(label="Prioridade", choices=priorities, value=priorities[1] if len(priorities) > 1 else priorities[0] if priorities else None)
                    department = gr.Dropdown(label="Departamento", choices=departments, value=departments[0] if departments else None)
                    
                    submit_button = gr.Button("Processar E-mail")
                    result = gr.Textbox(label="Resultado", interactive=False)
            
            # Função de processamento
            def process_func(from_email, subject, body, category, priority, department, attachments):
                # Obtém caminhos dos anexos
                attachment_paths = [file.name for file in attachments] if attachments else []
                
                # Processa e-mail
                result = self._process_email(
                    from_email=from_email,
                    subject=subject,
                    body=body,
                    category=category,
                    priority=priority,
                    department=department,
                    attachments=attachment_paths
                )
                
                # Retorna mensagem de resultado
                return result['message']
            
            # Configura processamento
            submit_button.click(
                fn=process_func,
                inputs=[from_email, subject, body, category, priority, department, attachments],
                outputs=[result]
            )
        
        # Salva referência à interface
        self.interface = interface
        
        # Inicia interface
        interface.launch(share=share)

# Exemplo de uso
if __name__ == "__main__":
    # Cria formulário
    form = EmailForm()
    
    # Inicia formulário
    form.launch()
