# Sistema de Gerenciamento de Contratos Escolares

## Visão Geral

Este sistema foi desenvolvido para automatizar o processo de recebimento, análise e encaminhamento de e-mails relacionados a contratos escolares. Utilizando técnicas avançadas de processamento de linguagem natural e aprendizado de máquina, o sistema classifica o conteúdo dos e-mails e os encaminha para os setores responsáveis.

## Funcionalidades Principais

- **Análise de E-mails**: Conecta-se ao servidor de e-mail, lê mensagens e extrai informações relevantes
- **Classificação de Conteúdo**: Analisa o conteúdo dos e-mails para determinar o tipo de solicitação
- **Encaminhamento para Setores**: Direciona os e-mails para os setores responsáveis
- **Banco de Dados**: Armazena informações de contratos, escolas e histórico de comunicações
- **Segurança**: Implementa autenticação, controle de acesso e criptografia de dados sensíveis
- **Interface de Usuário**: Fornece uma interface amigável para gerenciamento do sistema

## Estrutura do Projeto

```
contract_manager/
├── email_analyzer/         # Módulo de análise de e-mails
│   ├── email_connector.py  # Conexão com servidor de e-mail
│   ├── email_reader.py     # Leitura de e-mails
│   ├── email_parser.py     # Análise de conteúdo
│   ├── attachment_processor.py  # Processamento de anexos
│   └── __init__.py
├── classifier/             # Módulo de classificação
│   ├── email_classifier.py  # Classificação de e-mails
│   ├── contract_matcher.py  # Correspondência com contratos
│   └── __init__.py
├── router/                 # Módulo de encaminhamento
│   ├── email_router.py     # Encaminhamento para setores
│   ├── notification_manager.py  # Notificações
│   └── __init__.py
├── database/               # Módulo de banco de dados
│   ├── contract_database.py  # Operações CRUD
│   └── __init__.py
├── security/               # Módulo de segurança
│   ├── security_manager.py  # Autenticação e criptografia
│   └── __init__.py
├── ui/                     # Interface de usuário
│   ├── dashboard.py        # Painel principal
│   ├── email_form.py       # Formulário de e-mails
│   ├── contract_form.py    # Formulário de contratos
│   └── __init__.py
├── app.py                  # Aplicação principal
├── config.json             # Configuração do sistema
├── requirements.txt        # Dependências
├── documentation.md        # Documentação técnica
└── tests.py                # Testes unitários
```

## Requisitos

- Python 3.10 ou superior
- Bibliotecas listadas em requirements.txt
- Acesso a servidor de e-mail (IMAP/POP3)
- Permissões para envio de e-mails (SMTP)

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/empresa/contract-manager.git
   cd contract-manager
   ```

2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure o sistema:
   ```bash
   cp config.example.json config.json
   # Edite config.json com suas configurações
   ```

5. Inicialize o banco de dados:
   ```bash
   python init_database.py
   ```

## Uso

1. Inicie a aplicação:
   ```bash
   python app.py
   ```

2. Acesse a interface web em `http://localhost:5000`

3. Faça login com as credenciais padrão:
   - Usuário: `admin`
   - Senha: `admin123`

## Documentação

Para informações detalhadas sobre o sistema, consulte o arquivo `documentation.md`.

## Testes

Execute os testes unitários com:
```bash
python -m unittest tests.py
```

## Segurança

O sistema implementa diversas medidas de segurança:
- Autenticação de usuários com senha segura
- Controle de acesso baseado em papéis
- Criptografia de dados sensíveis
- Proteção contra ataques CSRF, XSS e injeção
- Limitação de taxa de requisições
- Bloqueio de IP após múltiplas tentativas de login

## Suporte

Para suporte, entre em contato com:
- Email: suporte@empresa.com
- Telefone: (11) 1234-5678

## Licença

Este projeto é licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.
