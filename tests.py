import unittest
import os
import sys
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Adiciona diretório raiz ao path para importação de módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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


class TestEmailAnalyzer(unittest.TestCase):
    """Testes para o módulo de análise de e-mails"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.test_config = {
            'server': 'test.example.com',
            'port': 993,
            'username': 'test@example.com',
            'password': 'test_password',
            'use_ssl': True
        }
        
        # Cria diretório temporário para testes
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Limpeza após os testes"""
        # Remove diretório temporário
        shutil.rmtree(self.test_dir)
    
    @patch('imaplib.IMAP4_SSL')
    def test_email_connector(self, mock_imap):
        """Testa conexão com servidor de e-mail"""
        # Configura mock
        mock_instance = mock_imap.return_value
        mock_instance.login.return_value = ('OK', [b'Login successful'])
        
        # Testa conexão
        connector = EmailConnector(self.test_config)
        result = connector.connect()
        
        # Verifica resultados
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Conexão estabelecida com sucesso')
        
        # Verifica chamadas ao mock
        mock_imap.assert_called_once_with(
            self.test_config['server'], 
            self.test_config['port']
        )
        mock_instance.login.assert_called_once_with(
            self.test_config['username'], 
            self.test_config['password']
        )
    
    @patch('email_analyzer.email_reader.EmailReader._fetch_email_data')
    def test_email_reader(self, mock_fetch):
        """Testa leitura de e-mails"""
        # Configura mock
        mock_fetch.return_value = {
            'from': 'sender@example.com',
            'to': 'test@example.com',
            'subject': 'Teste de E-mail',
            'date': '2023-04-23',
            'body_text': 'Conteúdo de teste',
            'body_html': '<p>Conteúdo de teste</p>',
            'attachments': []
        }
        
        # Cria mock de conexão
        mock_connection = MagicMock()
        mock_connection.search.return_value = ('OK', [b'1 2 3'])
        
        # Testa leitura de e-mails
        reader = EmailReader(mock_connection)
        emails = reader.get_unread_emails(max_emails=2)
        
        # Verifica resultados
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]['from'], 'sender@example.com')
        self.assertEqual(emails[0]['subject'], 'Teste de E-mail')
        
        # Verifica chamadas ao mock
        mock_connection.search.assert_called_once_with(None, 'UNSEEN')
    
    def test_email_parser(self):
        """Testa análise de conteúdo de e-mail"""
        # Cria parser
        parser = EmailParser()
        
        # Testa extração de informações
        email_content = """
        Prezados,
        
        Gostaria de solicitar a renovação do contrato nº 12345 da Escola Municipal João da Silva.
        O contrato atual vence em 31/12/2023 e precisamos renovar por mais 12 meses.
        
        Valor atual: R$ 5.000,00
        
        Atenciosamente,
        Maria Silva
        Diretora
        Tel: (11) 98765-4321
        """
        
        result = parser.extract_information(email_content)
        
        # Verifica resultados
        self.assertIn('contrato', result['keywords'])
        self.assertIn('renovação', result['keywords'])
        self.assertIn('12345', result['contract_numbers'])
        self.assertIn('Escola Municipal João da Silva', result['entities'])
        self.assertIn('R$ 5.000,00', result['values'])
        self.assertIn('31/12/2023', result['dates'])
    
    def test_attachment_processor(self):
        """Testa processamento de anexos"""
        # Cria processador
        processor = AttachmentProcessor()
        
        # Cria arquivo de teste
        test_file_path = os.path.join(self.test_dir, 'test.txt')
        with open(test_file_path, 'w') as f:
            f.write("Contrato nº 12345\nEscola Municipal João da Silva\nValor: R$ 5.000,00")
        
        # Testa processamento
        result = processor.process_attachment(test_file_path)
        
        # Verifica resultados
        self.assertTrue(result['success'])
        self.assertIn('contrato', result['content_info']['keywords'])
        self.assertIn('12345', result['content_info']['contract_numbers'])
        self.assertIn('Escola Municipal João da Silva', result['content_info']['entities'])
        self.assertIn('R$ 5.000,00', result['content_info']['values'])


class TestClassifier(unittest.TestCase):
    """Testes para o módulo de classificação"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        pass
    
    def test_email_classifier(self):
        """Testa classificação de e-mails"""
        # Cria classificador
        classifier = EmailClassifier()
        
        # Testa classificação
        test_cases = [
            {
                'content': "Gostaria de solicitar a renovação do contrato nº 12345.",
                'expected_category': 'renovacao'
            },
            {
                'content': "Estamos enviando o novo contrato para assinatura.",
                'expected_category': 'novo_contrato'
            },
            {
                'content': "Precisamos de informações sobre o pagamento da fatura.",
                'expected_category': 'pagamento'
            },
            {
                'content': "Estamos com problemas no sistema de acesso.",
                'expected_category': 'suporte'
            }
        ]
        
        for test in test_cases:
            result = classifier.classify(test['content'])
            self.assertEqual(result['category'], test['expected_category'])
            self.assertGreaterEqual(result['confidence'], 0.7)
    
    def test_contract_matcher(self):
        """Testa correspondência de contratos"""
        # Cria matcher
        matcher = ContractMatcher()
        
        # Testa correspondência
        content = """
        Referente ao contrato CONT-2023-001 da Escola Municipal João da Silva.
        Também precisamos verificar o contrato nº 12345 da Escola Estadual Maria Santos.
        """
        
        result = matcher.find_contract_references(content)
        
        # Verifica resultados
        self.assertIn('CONT-2023-001', result['contract_numbers'])
        self.assertIn('12345', result['contract_numbers'])
        self.assertIn('Escola Municipal João da Silva', result['schools'])
        self.assertIn('Escola Estadual Maria Santos', result['schools'])


class TestRouter(unittest.TestCase):
    """Testes para o módulo de encaminhamento"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        # Configuração de teste
        self.test_config = {
            'departments': {
                'novo_contrato': ['contratos@empresa.com'],
                'renovacao': ['renovacoes@empresa.com'],
                'pagamento': ['financeiro@empresa.com'],
                'suporte': ['suporte@empresa.com']
            }
        }
    
    def test_email_router(self):
        """Testa encaminhamento de e-mails"""
        # Cria roteador
        router = EmailRouter(self.test_config)
        
        # Testa encaminhamento
        email_data = {
            'id': 'email123',
            'from': 'escola@exemplo.com',
            'subject': 'Renovação de Contrato',
            'content': 'Conteúdo de teste',
            'classification': {
                'category': 'renovacao',
                'priority': 'alta'
            }
        }
        
        result = router.route_email(email_data)
        
        # Verifica resultados
        self.assertEqual(result['department'], 'renovacao')
        self.assertEqual(result['assignees'], ['renovacoes@empresa.com'])
    
    @patch('smtplib.SMTP_SSL')
    def test_notification_manager(self, mock_smtp):
        """Testa envio de notificações"""
        # Configura mock
        mock_instance = mock_smtp.return_value
        mock_instance.login.return_value = None
        mock_instance.sendmail.return_value = {}
        
        # Configuração de teste
        smtp_config = {
            'server': 'smtp.example.com',
            'port': 465,
            'username': 'notificacoes@empresa.com',
            'password': 'senha_segura',
            'use_ssl': True
        }
        
        # Cria gerenciador de notificações
        notifier = NotificationManager(smtp_config)
        
        # Testa envio de notificação
        result = notifier.send_notification(
            recipients=['destinatario@exemplo.com'],
            subject='Teste de Notificação',
            message='Conteúdo da notificação de teste'
        )
        
        # Verifica resultados
        self.assertTrue(result['success'])
        
        # Verifica chamadas ao mock
        mock_smtp.assert_called_once_with(
            smtp_config['server'], 
            smtp_config['port']
        )
        mock_instance.login.assert_called_once_with(
            smtp_config['username'], 
            smtp_config['password']
        )
        mock_instance.sendmail.assert_called_once()


class TestDatabase(unittest.TestCase):
    """Testes para o módulo de banco de dados"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        # Cria banco de dados temporário para testes
        self.test_db_path = os.path.join(tempfile.mkdtemp(), 'test_contracts.db')
        self.db = ContractDatabase(db_path=self.test_db_path)
    
    def tearDown(self):
        """Limpeza após os testes"""
        # Remove arquivo de banco de dados
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_add_contract(self):
        """Testa adição de contrato"""
        # Dados de teste
        contract_data = {
            'contract_number': 'CONT-2023-001',
            'school_name': 'Escola Municipal João da Silva',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'value': 'R$ 5.000,00',
            'status': 'Ativo',
            'contract_type': 'Fornecimento de Material'
        }
        
        # Adiciona contrato
        result = self.db.add_contract(contract_data, user='test_user')
        
        # Verifica resultados
        self.assertTrue(result['success'])
        
        # Verifica se o contrato foi adicionado
        contracts = self.db.search_contracts(search_term='João da Silva')
        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0]['contract_number'], 'CONT-2023-001')
    
    def test_update_contract(self):
        """Testa atualização de contrato"""
        # Adiciona contrato para teste
        contract_data = {
            'contract_number': 'CONT-2023-002',
            'school_name': 'Escola Estadual Maria Santos',
            'start_date': '2023-02-01',
            'end_date': '2023-12-31',
            'value': 'R$ 7.500,00',
            'status': 'Ativo',
            'contract_type': 'Serviços de Limpeza'
        }
        
        self.db.add_contract(contract_data, user='test_user')
        
        # Atualiza contrato
        update_data = {
            'value': 'R$ 8.000,00',
            'status': 'Renovado'
        }
        
        result = self.db.update_contract('CONT-2023-002', update_data, user='test_user')
        
        # Verifica resultados
        self.assertTrue(result['success'])
        
        # Verifica se o contrato foi atualizado
        contracts = self.db.search_contracts(search_term='Maria Santos')
        self.assertEqual(contracts[0]['value'], 'R$ 8.000,00')
        self.assertEqual(contracts[0]['status'], 'Renovado')
    
    def test_search_contracts(self):
        """Testa pesquisa de contratos"""
        # Adiciona contratos para teste
        contracts = [
            {
                'contract_number': 'CONT-2023-003',
                'school_name': 'Escola Municipal Pedro Alves',
                'start_date': '2023-03-01',
                'end_date': '2023-12-31',
                'value': 'R$ 4.500,00',
                'status': 'Ativo',
                'contract_type': 'Fornecimento de Material'
            },
            {
                'contract_number': 'CONT-2023-004',
                'school_name': 'Escola Municipal Ana Lima',
                'start_date': '2023-03-15',
                'end_date': '2023-12-31',
                'value': 'R$ 6.000,00',
                'status': 'Pendente',
                'contract_type': 'Serviços de Limpeza'
            }
        ]
        
        for contract in contracts:
            self.db.add_contract(contract, user='test_user')
        
        # Testa pesquisa por termo
        results = self.db.search_contracts(search_term='Municipal')
        self.assertEqual(len(results), 2)
        
        # Testa pesquisa por status
        results = self.db.search_contracts(status='Pendente')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['school_name'], 'Escola Municipal Ana Lima')
        
        # Testa pesquisa por tipo de contrato
        results = self.db.search_contracts(contract_type='Fornecimento de Material')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['school_name'], 'Escola Municipal Pedro Alves')


class TestSecurity(unittest.TestCase):
    """Testes para o módulo de segurança"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        # Cria diretório temporário para testes
        self.test_dir = tempfile.mkdtemp()
        
        # Configuração de teste
        self.test_config_path = os.path.join(self.test_dir, 'test_config.json')
        self.test_config = {
            'security': {
                'users_file': os.path.join(self.test_dir, 'users.json'),
                'encryption_key_file': os.path.join(self.test_dir, 'encryption.key'),
                'password_min_length': 8,
                'password_require_uppercase': True,
                'password_require_lowercase': True,
                'password_require_numbers': True,
                'password_require_special': True,
                'session_timeout': 3600,
                'max_login_attempts': 3,
                'lockout_duration': 300,
                'sensitive_fields': [
                    'value',
                    'payment_amount',
                    'email',
                    'phone'
                ]
            }
        }
        
        # Salva configuração
        with open(self.test_config_path, 'w') as f:
            json.dump(self.test_config, f)
        
        # Cria gerenciador de segurança
        self.security = SecurityManager(self.test_config_path)
    
    def tearDown(self):
        """Limpeza após os testes"""
        # Remove diretório temporário
        shutil.rmtree(self.test_dir)
    
    def test_user_management(self):
        """Testa gerenciamento de usuários"""
        # Cria usuário
        result = self.security.create_user(
            username='testuser',
            password='Test@123',
            role='manager',
            name='Usuário de Teste',
            email='testuser@example.com'
        )
        
        # Verifica resultados
        self.assertTrue(result['success'])
        
        # Verifica se o usuário foi criado
        users = self.security.get_users()
        self.assertEqual(len(users), 2)  # admin + testuser
        
        # Encontra o usuário criado
        test_user = next((user for user in users if user['username'] == 'testuser'), None)
        self.assertIsNotNone(test_user)
        self.assertEqual(test_user['name'], 'Usuário de Teste')
        self.assertEqual(test_user['role'], 'manager')
        
        # Atualiza usuário
        update_result = self.security.update_user(
            username='testuser',
            data={
                'name': 'Nome Atualizado',
                'role': 'user'
            }
        )
        
        self.assertTrue(update_result['success'])
        
        # Verifica se o usuário foi atualizado
        users = self.security.get_users()
        test_user = next((user for user in users if user['username'] == 'testuser'), None)
        self.assertEqual(test_user['name'], 'Nome Atualizado')
        self.assertEqual(test_user['role'], 'user')
        
        # Remove usuário
        delete_result = self.security.delete_user('testuser')
        self.assertTrue(delete_result['success'])
        
        # Verifica se o usuário foi removido
        users = self.security.get_users()
        test_user = next((user for user in users if user['username'] == 'testuser'), None)
        self.assertIsNone(test_user)
    
    def test_authentication(self):
        """Testa autenticação de usuários"""
        # Cria usuário para teste
        self.security.create_user(
            username='authuser',
            password='Auth@123',
            role='user',
            name='Usuário de Autenticação',
            email='authuser@example.com'
        )
        
        # Testa autenticação com credenciais corretas
        auth_result = self.security.authenticate_user(
            username='authuser',
            password='Auth@123'
        )
        
        self.assertTrue(auth_result['success'])
        self.assertIn('session_token', auth_result['user'])
        
        # Testa autenticação com senha incorreta
        auth_result = self.security.authenticate_user(
            username='authuser',
            password='senha_incorreta'
        )
        
        self.assertFalse(auth_result['success'])
        
        # Testa bloqueio após múltiplas tentativas
        for _ in range(3):  # max_login_attempts
            self.security.authenticate_user(
                username='authuser',
                password='senha_incorreta'
            )
        
        # Verifica se o usuário foi bloqueado
        auth_result = self.security.authenticate_user(
            username='authuser',
            password='Auth@123'  # senha correta
        )
        
        self.assertFalse(auth_result['success'])
        self.assertIn('bloqueado', auth_result['message'])
    
    def test_access_control(self):
        """Testa controle de acesso"""
        # Cria usuários com diferentes papéis
        self.security.create_user(
            username='adminuser',
            password='Admin@123',
            role='admin',
            name='Administrador',
            email='admin@example.com'
        )
        
        self.security.create_user(
            username='manageruser',
            password='Manager@123',
            role='manager',
            name='Gerente',
            email='manager@example.com'
        )
        
        self.security.create_user(
            username='regularuser',
            password='User@123',
            role='user',
            name='Usuário Regular',
            email='user@example.com'
        )
        
        # Testa acesso de administrador
        access_result = self.security.validate_access(
            username='adminuser',
            resource='users',
            action='create'
        )
        
        self.assertTrue(access_result['allowed'])
        
        # Testa acesso de gerente
        access_result = self.security.validate_access(
            username='manageruser',
            resource='contracts',
            action='update'
        )
        
        self.assertTrue(access_result['allowed'])
        
        # Testa acesso negado para gerente
        access_result = self.security.validate_access(
            username='manageruser',
            resource='users',
            action='delete'
        )
        
        self.assertFalse(access_result['allowed'])
        
        # Testa acesso de usuário regular
        access_result = self.security.validate_access(
            username='regularuser',
            resource='contracts',
            action='read'
        )
        
        self.assertTrue(access_result['allowed'])
        
        # Testa acesso negado para usuário regular
        access_result = self.security.validate_access(
            username='regularuser',
            resource='contracts',
            action='create'
        )
        
        self.assertFalse(access_result['allowed'])
    
    def test_encryption(self):
        """Testa criptografia de dados"""
        # Dados de teste
        test_data = {
            'contract_number': 'CONT-2023-005',
            'school_name': 'Escola Teste',
            'value': 'R$ 10.000,00',
            'email': 'escola@exemplo.com',
            'phone': '(11) 98765-4321',
            'description': 'Descrição do contrato'
        }
        
        # Criptografa dados sensíveis
        encrypted_data = self.security.encrypt_sensitive_fields(test_data)
        
        # Verifica se campos sensíveis foram criptografados
        self.assertTrue(str(encrypted_data['value']).startswith('encrypted:'))
        self.assertTrue(str(encrypted_data['email']).startswith('encrypted:'))
        self.assertTrue(str(encrypted_data['phone']).startswith('encrypted:'))
        
        # Verifica se campos não sensíveis não foram criptografados
        self.assertEqual(encrypted_data['contract_number'], 'CONT-2023-005')
        self.assertEqual(encrypted_data['school_name'], 'Escola Teste')
        self.assertEqual(encrypted_data['description'], 'Descrição do contrato')
        
        # Descriptografa dados
        decrypted_data = self.security.decrypt_sensitive_fields(encrypted_data)
        
        # Verifica se dados foram descriptografados corretamente
        self.assertEqual(decrypted_data['value'], 'R$ 10.000,00')
        self.assertEqual(decrypted_data['email'], 'escola@exemplo.com')
        self.assertEqual(decrypted_data['phone'], '(11) 98765-4321')


if __name__ == '__main__':
    unittest.main()
