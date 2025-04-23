import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_router")

class EmailRouter:
    """
    Classe responsável por encaminhar e-mails para os departamentos apropriados.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o roteador de e-mails.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Mapeamento de departamentos para e-mails
        self.department_emails = self.config.get('department_emails', {})
        
        # Configuração de SMTP
        self.smtp_config = self.config.get('smtp', {})
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do roteador.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Dict[str, Any]: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'department_emails': {
                'comercial': 'comercial@empresa.com',
                'juridico': 'juridico@empresa.com',
                'financeiro': 'financeiro@empresa.com',
                'atendimento': 'atendimento@empresa.com',
                'suporte_tecnico': 'suporte@empresa.com',
                'triagem': 'triagem@empresa.com'
            },
            'smtp': {
                'server': 'smtp.empresa.com',
                'port': 587,
                'username': 'sistema@empresa.com',
                'password': 'senha',
                'use_tls': True,
                'from_email': 'sistema@empresa.com',
                'from_name': 'Sistema de Contratos'
            },
            'templates': {
                'forward_subject': '[Encaminhamento] {original_subject}',
                'forward_body': '''
                    <html>
                    <body>
                    <p>Este e-mail foi encaminhado automaticamente para o departamento de {department}.</p>
                    <p><strong>Categoria:</strong> {category}<br>
                    <strong>Prioridade:</strong> {priority}<br>
                    <strong>Recebido em:</strong> {received_date}</p>
                    
                    <hr>
                    <h3>E-mail Original</h3>
                    <p><strong>De:</strong> {original_from}<br>
                    <strong>Assunto:</strong> {original_subject}<br>
                    <strong>Data:</strong> {original_date}</p>
                    
                    <div style="border-left: 2px solid #ccc; padding-left: 10px;">
                    {original_body}
                    </div>
                    
                    <hr>
                    <p>Este é um encaminhamento automático. Por favor, não responda diretamente a este e-mail.</p>
                    </body>
                    </html>
                ''',
                'auto_reply_subject': 'Recebemos seu e-mail: {original_subject}',
                'auto_reply_body': '''
                    <html>
                    <body>
                    <p>Prezado(a) {sender_name},</p>
                    
                    <p>Recebemos seu e-mail com o assunto "{original_subject}" e ele foi encaminhado para o departamento responsável.</p>
                    
                    <p>Seu e-mail será analisado em breve por nossa equipe.</p>
                    
                    <p>Número de protocolo: {protocol_number}</p>
                    
                    <p>Atenciosamente,<br>
                    Equipe de Contratos</p>
                    
                    <hr>
                    <p><small>Este é um e-mail automático. Por favor, não responda diretamente a este e-mail.</small></p>
                    </body>
                    </html>
                '''
            },
            'notification': {
                'send_auto_reply': True,
                'cc_to_triagem': True
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
    
    def route_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encaminha um e-mail para o departamento apropriado.
        
        Args:
            email: E-mail classificado
            
        Returns:
            Dict[str, Any]: E-mail com informações de encaminhamento
        """
        try:
            # Cria cópia do e-mail para não modificar o original
            routed_email = email.copy()
            
            # Determina o departamento de destino
            department = email.get('department', 'triagem')
            
            # Obtém e-mail do departamento
            department_email = self.department_emails.get(department)
            
            if not department_email:
                logger.warning(f"E-mail do departamento '{department}' não encontrado, usando triagem")
                department = 'triagem'
                department_email = self.department_emails.get('triagem')
            
            # Se ainda não houver e-mail de departamento, não encaminha
            if not department_email:
                logger.error("Nenhum e-mail de departamento encontrado, não é possível encaminhar")
                routed_email['routing_status'] = 'error'
                routed_email['routing_error'] = 'Nenhum e-mail de departamento encontrado'
                return routed_email
            
            # Encaminha o e-mail
            forwarding_result = self._forward_email(email, department, department_email)
            
            # Adiciona informações de encaminhamento ao e-mail
            routed_email['routing_status'] = 'success' if forwarding_result else 'error'
            routed_email['routed_to_department'] = department
            routed_email['routed_to_email'] = department_email
            routed_email['routing_date'] = datetime.datetime.now().isoformat()
            
            # Envia resposta automática se configurado
            if self.config.get('notification', {}).get('send_auto_reply', True):
                self._send_auto_reply(email)
            
            return routed_email
        
        except Exception as e:
            logger.error(f"Erro ao encaminhar e-mail: {str(e)}")
            # Retorna o e-mail original com erro
            email['routing_status'] = 'error'
            email['routing_error'] = str(e)
            return email
    
    def _forward_email(self, email: Dict[str, Any], department: str, to_email: str) -> bool:
        """
        Encaminha um e-mail para um departamento.
        
        Args:
            email: E-mail a ser encaminhado
            department: Nome do departamento
            to_email: E-mail de destino
            
        Returns:
            bool: True se o encaminhamento foi bem-sucedido, False caso contrário
        """
        try:
            # Obtém configuração SMTP
            smtp_server = self.smtp_config.get('server', '')
            smtp_port = self.smtp_config.get('port', 587)
            smtp_username = self.smtp_config.get('username', '')
            smtp_password = self.smtp_config.get('password', '')
            use_tls = self.smtp_config.get('use_tls', True)
            from_email = self.smtp_config.get('from_email', '')
            from_name = self.smtp_config.get('from_name', 'Sistema de Contratos')
            
            # Verifica se há configuração SMTP
            if not smtp_server or not smtp_username or not smtp_password or not from_email:
                logger.error("Configuração SMTP incompleta, não é possível enviar e-mail")
                return False
            
            # Cria mensagem
            msg = MIMEMultipart('alternative')
            
            # Define cabeçalhos
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = to_email
            
            # Adiciona CC para triagem se configurado
            if department != 'triagem' and self.config.get('notification', {}).get('cc_to_triagem', True):
                triagem_email = self.department_emails.get('triagem')
                if triagem_email:
                    msg['Cc'] = triagem_email
            
            # Define assunto
            original_subject = email.get('subject', 'Sem assunto')
            forward_subject_template = self.config.get('templates', {}).get('forward_subject', '[Encaminhamento] {original_subject}')
            subject = forward_subject_template.format(original_subject=original_subject)
            msg['Subject'] = subject
            
            # Prepara corpo do e-mail
            original_from = email.get('from', 'desconhecido')
            original_date = email.get('date', 'desconhecido')
            original_body = email.get('body', '')
            
            # Converte corpo para HTML se for texto simples
            if not original_body.strip().startswith('<'):
                original_body = original_body.replace('\n', '<br>')
            
            # Formata corpo do e-mail
            forward_body_template = self.config.get('templates', {}).get('forward_body', '')
            body = forward_body_template.format(
                department=department,
                category=email.get('ml_category', email.get('category', 'desconhecido')),
                priority=email.get('ml_priority', email.get('priority', 'normal')),
                received_date=datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                original_from=original_from,
                original_subject=original_subject,
                original_date=original_date,
                original_body=original_body
            )
            
            # Adiciona corpo HTML
            msg.attach(MIMEText(body, 'html'))
            
            # Adiciona anexos originais
            if 'attachments' in email:
                for attachment in email['attachments']:
                    path = attachment.get('saved_path', attachment.get('path', ''))
                    if path and os.path.exists(path):
                        filename = attachment.get('filename', os.path.basename(path))
                        
                        with open(path, 'rb') as f:
                            part = MIMEApplication(f.read(), Name=filename)
                        
                        part['Content-Disposition'] = f'attachment; filename="{filename}"'
                        msg.attach(part)
            
            # Envia e-mail
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                
                server.login(smtp_username, smtp_password)
                
                # Define destinatários
                recipients = [to_email]
                
                # Adiciona CC para triagem
                if department != 'triagem' and self.config.get('notification', {}).get('cc_to_triagem', True):
                    triagem_email = self.department_emails.get('triagem')
                    if triagem_email:
                        recipients.append(triagem_email)
                
                server.sendmail(from_email, recipients, msg.as_string())
            
            logger.info(f"E-mail encaminhado com sucesso para {department} ({to_email})")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao encaminhar e-mail: {str(e)}")
            return False
    
    def _send_auto_reply(self, email: Dict[str, Any]) -> bool:
        """
        Envia resposta automática ao remetente original.
        
        Args:
            email: E-mail original
            
        Returns:
            bool: True se o envio foi bem-sucedido, False caso contrário
        """
        try:
            # Obtém e-mail do remetente
            from_addr = email.get('from', '')
            
            # Extrai e-mail do remetente
            import re
            email_match = re.search(r'<([^>]+)>', from_addr)
            if email_match:
                sender_email = email_match.group(1)
            else:
                sender_email = from_addr
            
            # Verifica se há e-mail do remetente
            if not sender_email:
                logger.warning("E-mail do remetente não encontrado, não é possível enviar resposta automática")
                return False
            
            # Extrai nome do remetente
            name_match = re.search(r'^([^<]+)', from_addr)
            if name_match:
                sender_name = name_match.group(1).strip()
            else:
                sender_name = sender_email.split('@')[0]
            
            # Obtém configuração SMTP
            smtp_server = self.smtp_config.get('server', '')
            smtp_port = self.smtp_config.get('port', 587)
            smtp_username = self.smtp_config.get('username', '')
            smtp_password = self.smtp_config.get('password', '')
            use_tls = self.smtp_config.get('use_tls', True)
            from_email = self.smtp_config.get('from_email', '')
            from_name = self.smtp_config.get('from_name', 'Sistema de Contratos')
            
            # Verifica se há configuração SMTP
            if not smtp_server or not smtp_username or not smtp_password or not from_email:
                logger.error("Configuração SMTP incompleta, não é possível enviar e-mail")
                return False
            
            # Cria mensagem
            msg = MIMEMultipart('alternative')
            
            # Define cabeçalhos
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = sender_email
            
            # Define assunto
            original_subject = email.get('subject', 'Sem assunto')
            auto_reply_subject_template = self.config.get('templates', {}).get('auto_reply_subject', 'Recebemos seu e-mail: {original_subject}')
            subject = auto_reply_subject_template.format(original_subject=original_subject)
            msg['Subject'] = subject
            
            # Gera número de protocolo
            import uuid
            protocol_number = str(uuid.uuid4()).upper()[:8]
            
            # Formata corpo do e-mail
            auto_reply_body_template = self.config.get('templates', {}).get('auto_reply_body', '')
            body = auto_reply_body_template.format(
                sender_name=sender_name,
                original_subject=original_subject,
                protocol_number=protocol_number
            )
            
            # Adiciona corpo HTML
            msg.attach(MIMEText(body, 'html'))
            
            # Envia e-mail
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.sendmail(from_email, [sender_email], msg.as_string())
            
            logger.info(f"Resposta automática enviada para {sender_email}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao enviar resposta automática: {str(e)}")
            return False

# Exemplo de uso
if __name__ == "__main__":
    # Cria roteador
    router = EmailRouter()
    
    # Exemplo de e-mail classificado
    email = {
        'id': '123',
        'subject': 'Renovação de Contrato - Escola Municipal João da Silva',
        'from': 'Maria Oliveira <maria@escola.edu.br>',
        'to': 'contratos@empresa.com',
        'date': '2023-04-15',
        'body': '''
        Prezados,
        
        Solicito a renovação do contrato nº 12345 da Escola Municipal João da Silva.
        O contrato atual vence em 30/05/2023 e gostaríamos de renová-lo por mais 12 meses.
        
        O valor atual é de R$ 5.000,00 mensais.
        
        Atenciosamente,
        Maria Oliveira
        Diretora
        Tel: (11) 98765-4321
        ''',
        'attachments': [],
        'entities': {
            'contract_numbers': ['12345'],
            'school_names': ['Escola Municipal João da Silva'],
            'dates': ['30/05/2023'],
            'value': ['R$ 5.000,00']
        },
        'ml_category': 'renovacao',
        'ml_category_confidence': 0.85,
        'ml_priority': 'normal',
        'ml_priority_confidence': 0.75,
        'department': 'comercial',
        'department_confidence': 0.9
    }
    
    # Encaminha e-mail
    routed_email = router.route_email(email)
    
    # Exibe resultados
    print(f"Status de encaminhamento: {routed_email['routing_status']}")
    if routed_email['routing_status'] == 'success':
        print(f"Encaminhado para: {routed_email['routed_to_department']} ({routed_email['routed_to_email']})")
        print(f"Data de encaminhamento: {routed_email['routing_date']}")
    else:
        print(f"Erro de encaminhamento: {routed_email.get('routing_error', 'desconhecido')}")
