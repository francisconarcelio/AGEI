#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aplicação principal do Sistema de Gerenciamento de Contratos Escolares.
Este arquivo integra todos os módulos do sistema e inicia a aplicação web.
"""

import os
import logging
import json
import argparse
import threading
import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

# Importa módulos do sistema
from email_analyzer.email_connector import EmailConnector
from email_analyzer.email_reader import EmailReader
from email_analyzer.email_parser import EmailParser
from email_analyzer.attachment_processor import AttachmentProcessor
from classifier.email_classifier import EmailClassifier
from classifier.contract_matcher import ContractMatcher
from router.email_router import EmailRouter
from router.notification_manager import NotificationManager
from database.contract_database import ContractDatabase
from security.security_manager import SecurityManager
from ui.dashboard import create_dashboard
from ui.email_form import create_email_form
from ui.contract_form import create_contract_form

class ContractManagerApp:
    """
    Classe principal da aplicação de gerenciamento de contratos escolares.
    """
    
    def __init__(self, config_path=None):
        """
        Inicializa a aplicação.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Cria diretórios necessários
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('backups', exist_ok=True)
        
        # Carrega configuração
        self.config_path = config_path or 'config.json'
        self.config = self._load_config()
        
        # Inicializa componentes
        self._init_components()
        
        # Cria aplicação Flask
        self.app = Flask(__name__)
        self.app.secret_key = self.config.get('app', {}).get('secret_key', os.urandom(24).hex())
        
        # Configura rotas
        self._setup_routes()
        
        # Flag para controle do processamento de e-mails em background
        self.running = False
    
    def _load_config(self):
        """
        Carrega configuração da aplicação.
        
        Returns:
            dict: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'app': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'secret_key': os.urandom(24).hex()
            },
            'email': {
                'server': 'imap.example.com',
                'port': 993,
                'username': 'contratos@empresa.com',
                'password': 'senha_segura',
                'use_ssl': True,
                'check_interval': 300  # 5 minutos
            },
            'database': {
                'db_path': 'data/contracts.db',
                'backup_enabled': True,
                'backup_interval': 86400,  # 24 horas
                'backup_path': 'backups/',
                'max_backups': 7
            },
            'security': {
                'users_file': 'data/users.json',
                'encryption_key_file': 'data/encryption.key',
                'password_min_length': 8,
                'session_timeout': 3600,  # 1 hora
                'max_login_attempts': 5
            },
            'departments': {
                'novo_contrato': ['contratos@empresa.com'],
                'renovacao': ['renovacoes@empresa.com'],
                'pagamento': ['financeiro@empresa.com'],
                'suporte': ['suporte@empresa.com']
            }
        }
        
        # Verifica se o arquivo de configuração existe
        if not os.path.exists(self.config_path):
            logger.warning(f"Arquivo de configuração não encontrado: {self.config_path}")
            logger.info("Criando arquivo de configuração padrão")
            
            # Cria arquivo de configuração padrão
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
        
        try:
            # Carrega configuração do arquivo
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Configuração carregada de {self.config_path}")
            
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
            logger.error(f"Erro ao carregar configuração: {str(e)}")
            logger.warning("Usando configuração padrão")
            return default_config
    
    def _init_components(self):
        """
        Inicializa componentes do sistema.
        """
        try:
            # Inicializa banco de dados
            self.db = ContractDatabase(
                db_path=self.config['database']['db_path'],
                config_path=self.config_path
            )
            
            # Inicializa segurança
            self.security = SecurityManager(self.config_path)
            
            # Inicializa classificador
            self.classifier = EmailClassifier()
            
            # Inicializa matcher de contratos
            self.contract_matcher = ContractMatcher()
            
            # Inicializa roteador
            self.router = EmailRouter(self.config)
            
            # Inicializa notificador
            self.notifier = NotificationManager(self.config.get('email', {}))
            
            logger.info("Componentes inicializados com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao inicializar componentes: {str(e)}")
            raise
    
    def _setup_routes(self):
        """
        Configura rotas da aplicação Flask.
        """
        # Rota principal
        @self.app.route('/')
        def index():
            # Verifica se o usuário está autenticado
            if 'username' not in session:
                return redirect(url_for('login'))
            
            # Verifica se a sessão é válida
            session_result = self.security.validate_session(
                username=session['username'],
                session_token=session.get('session_token', '')
            )
            
            if not session_result['valid']:
                # Limpa sessão
                session.clear()
                return redirect(url_for('login'))
            
            # Renderiza dashboard
            return create_dashboard(self.db, self.security, session)
        
        # Rota de login
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            error = None
            
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                
                # Autentica usuário
                auth_result = self.security.authenticate_user(username, password)
                
                if auth_result['success']:
                    # Armazena informações na sessão
                    session['username'] = username
                    session['name'] = auth_result['user']['name']
                    session['role'] = auth_result['user']['role']
                    session['session_token'] = auth_result['user']['session_token']
                    
                    # Registra evento de segurança
                    self.security.log_security_event(
                        event_type="login_success",
                        username=username,
                        details={
                            'ip_address': request.remote_addr
                        }
                    )
                    
                    return redirect(url_for('index'))
                else:
                    error = auth_result['message']
                    
                    # Registra evento de segurança
                    self.security.log_security_event(
                        event_type="login_failure",
                        username=username,
                        details={
                            'ip_address': request.remote_addr,
                            'reason': auth_result['message']
                        }
                    )
            
            return render_template('login.html', error=error)
        
        # Rota de logout
        @self.app.route('/logout')
        def logout():
            # Registra evento de segurança
            if 'username' in session:
                self.security.log_security_event(
                    event_type="logout",
                    username=session['username'],
                    details={
                        'ip_address': request.remote_addr
                    }
                )
            
            # Limpa sessão
            session.clear()
            
            return redirect(url_for('login'))
        
        # Rota de e-mails
        @self.app.route('/emails', methods=['GET', 'POST'])
        def emails():
            # Verifica se o usuário está autenticado
            if 'username' not in session:
                return redirect(url_for('login'))
            
            # Verifica se a sessão é válida
            session_result = self.security.validate_session(
                username=session['username'],
                session_token=session.get('session_token', '')
            )
            
            if not session_result['valid']:
                # Limpa sessão
                session.clear()
                return redirect(url_for('login'))
            
            # Renderiza formulário de e-mails
            return create_email_form(
                self.db,
                self.security,
                self.classifier,
                self.router,
                session,
                request
            )
        
        # Rota de contratos
        @self.app.route('/contracts', methods=['GET', 'POST'])
        def contracts():
            # Verifica se o usuário está autenticado
            if 'username' not in session:
                return redirect(url_for('login'))
            
            # Verifica se a sessão é válida
            session_result = self.security.validate_session(
                username=session['username'],
                session_token=session.get('session_token', '')
            )
            
            if not session_result['valid']:
                # Limpa sessão
                session.clear()
                return redirect(url_for('login'))
            
            # Renderiza formulário de contratos
            return create_contract_form(
                self.db,
                self.security,
                session,
                request
            )
        
        # Rota de API para contratos
        @self.app.route('/api/contracts', methods=['GET'])
        def api_contracts():
            # Verifica autenticação via token
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    'error': 'Token de autenticação ausente ou inválido'
                }), 401
            
            token = auth_header[7:]  # Remove 'Bearer '
            
            # Verifica token
            # Implementação simplificada - em produção, usar JWT ou OAuth
            if token != self.app.secret_key:
                return jsonify({
                    'error': 'Token de autenticação inválido'
                }), 401
            
            # Parâmetros de consulta
            search = request.args.get('search', '')
            status = request.args.get('status', '')
            limit = int(request.args.get('limit', 10))
            offset = int(request.args.get('offset', 0))
            
            # Busca contratos
            contracts = self.db.search_contracts(
                search_term=search,
                status=status,
                limit=limit,
                offset=offset
            )
            
            # Conta total
            total = self.db.count_contracts(
                search_term=search,
                status=status
            )
            
            return jsonify({
                'total': total,
                'limit': limit,
                'offset': offset,
                'contracts': contracts
            })
        
        # Rota de API para e-mails
        @self.app.route('/api/emails', methods=['GET'])
        def api_emails():
            # Verifica autenticação via token
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    'error': 'Token de autenticação ausente ou inválido'
                }), 401
            
            token = auth_header[7:]  # Remove 'Bearer '
            
            # Verifica token
            # Implementação simplificada - em produção, usar JWT ou OAuth
            if token != self.app.secret_key:
                return jsonify({
                    'error': 'Token de autenticação inválido'
                }), 401
            
            # Parâmetros de consulta
            status = request.args.get('status', '')
            category = request.args.get('category', '')
            limit = int(request.args.get('limit', 10))
            offset = int(request.args.get('offset', 0))
            
            # Busca e-mails
            # Implementação simplificada - em produção, usar tabela de e-mails no banco de dados
            emails = []
            
            return jsonify({
                'total': len(emails),
                'limit': limit,
                'offset': offset,
                'emails': emails
            })
    
    def _process_emails(self):
        """
        Processa e-mails em background.
        """
        logger.info("Iniciando processamento de e-mails em background")
        
        while self.running:
            try:
                # Conecta ao servidor de e-mail
                email_config = self.config.get('email', {})
                connector = EmailConnector(email_config)
                connection_result = connector.connect()
                
                if connection_result['success']:
                    connection = connection_result['connection']
                    
                    # Lê e-mails não lidos
                    reader = EmailReader(connection)
                    emails = reader.get_unread_emails(max_emails=10)
                    
                    logger.info(f"Encontrados {len(emails)} e-mails não lidos")
                    
                    # Processa cada e-mail
                    for email in emails:
                        try:
                            # Classifica e-mail
                            classification = self.classifier.classify(email['body_text'])
                            
                            # Busca referências de contrato
                            contract_refs = self.contract_matcher.find_contract_references(email['body_text'])
                            
                            # Adiciona informações ao e-mail
                            email['classification'] = classification
                            email['contract_references'] = contract_refs
                            
                            # Encaminha e-mail
                            routing_result = self.router.route_email(email)
                            
                            # Envia notificação
                            if routing_result['success']:
                                self.notifier.send_notification(
                                    recipients=routing_result['assignees'],
                                    subject=f"Novo e-mail: {email['subject']}",
                                    message=f"Um novo e-mail foi encaminhado para seu setor.\n\n"
                                            f"De: {email['from']}\n"
                                            f"Assunto: {email['subject']}\n"
                                            f"Categoria: {classification['category']}\n"
                                            f"Prioridade: {classification['priority']}\n\n"
                                            f"Acesse o sistema para mais detalhes."
                                )
                            
                            logger.info(f"E-mail processado: {email['subject']}")
                        
                        except Exception as e:
                            logger.error(f"Erro ao processar e-mail: {str(e)}")
                    
                    # Fecha conexão
                    connection.logout()
                
                # Aguarda intervalo configurado
                check_interval = email_config.get('check_interval', 300)  # 5 minutos
                time.sleep(check_interval)
            
            except Exception as e:
                logger.error(f"Erro no processamento de e-mails: {str(e)}")
                time.sleep(60)  # Aguarda 1 minuto em caso de erro
    
    def start_email_processing(self):
        """
        Inicia processamento de e-mails em background.
        """
        if not self.running:
            self.running = True
            self.email_thread = threading.Thread(target=self._process_emails)
            self.email_thread.daemon = True
            self.email_thread.start()
            logger.info("Processamento de e-mails iniciado")
    
    def stop_email_processing(self):
        """
        Para processamento de e-mails em background.
        """
        if self.running:
            self.running = False
            logger.info("Processamento de e-mails interrompido")
    
    def run(self):
        """
        Executa a aplicação.
        """
        try:
            # Inicia processamento de e-mails em background
            self.start_email_processing()
            
            # Inicia aplicação Flask
            host = self.config['app']['host']
            port = self.config['app']['port']
            debug = self.config['app']['debug']
            
            logger.info(f"Iniciando aplicação em {host}:{port}")
            self.app.run(host=host, port=port, debug=debug)
        
        except KeyboardInterrupt:
            logger.info("Aplicação interrompida pelo usuário")
        
        except Exception as e:
            logger.error(f"Erro ao executar aplicação: {str(e)}")
        
        finally:
            # Para processamento de e-mails
            self.stop_email_processing()


if __name__ == '__main__':
    # Parse argumentos de linha de comando
    parser = argparse.ArgumentParser(description='Sistema de Gerenciamento de Contratos Escolares')
    parser.add_argument('--config', help='Caminho para o arquivo de configuração')
    args = parser.parse_args()
    
    # Cria e executa aplicação
    app = ContractManagerApp(config_path=args.config)
    app.run()
