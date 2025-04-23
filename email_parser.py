import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import re
import json
import numpy as np
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_parser")

class EmailParser:
    """
    Classe responsável por analisar e-mails e extrair informações estruturadas.
    """
    
    def __init__(self):
        """Inicializa o parser de e-mails."""
        # Padrões para extração de informações
        self.patterns = {
            'contract_number': [
                r'contrato\s+n[º°]?\s*[:.]?\s*(\d{4,10}[-/]?[\dA-Z]{0,5})',
                r'contrato\s+(\d{4,10}[-/]?[\dA-Z]{0,5})',
                r'n[º°]?\s*[:.]?\s*(\d{4,10}[-/]?[\dA-Z]{0,5})',
                r'processo\s+n[º°]?\s*[:.]?\s*(\d{4,10}[-/]?[\dA-Z]{0,5})'
            ],
            'school_name': [
                r'escola\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]{3,50})',
                r'colégio\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]{3,50})',
                r'centro\s+educacional\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]{3,50})',
                r'e\.e\.\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]{3,50})',
                r'e\.m\.\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]{3,50})'
            ],
            'date': [
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{2}\.\d{2}\.\d{4})',
                r'(\d{2}-\d{2}-\d{4})',
                r'(\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4})'
            ],
            'value': [
                r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'valor\s+(?:de|:)?\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'(?:valor|montante|quantia)\s+(?:de|:)?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
            ],
            'deadline': [
                r'prazo\s+(?:de|:)?\s*(\d+)\s*(?:dias|meses|anos)',
                r'(?:válido|validade|vigência|vigencia)\s+(?:por|de)?\s*(\d+)\s*(?:dias|meses|anos)',
                r'(?:vencimento|término|termino)\s+em\s+(\d{2}/\d{2}/\d{4})'
            ],
            'contact': [
                r'(?:telefone|tel|fone)(?:\s+|:)(\(\d{2}\)\s*\d{4,5}-\d{4})',
                r'(?:celular|cel)(?:\s+|:)(\(\d{2}\)\s*\d{5}-\d{4})',
                r'(?:e-mail|email)(?:\s+|:)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
        }
        
        # Palavras-chave para categorização
        self.keywords = {
            'novo_contrato': [
                'novo contrato', 'proposta', 'contratação', 'adesão', 'início de parceria',
                'nova escola', 'novo cliente', 'iniciar contrato'
            ],
            'renovacao': [
                'renovação', 'renovar', 'prorrogação', 'prorrogar', 'extensão', 'estender',
                'continuidade', 'continuar', 'manter contrato'
            ],
            'alteracao': [
                'alteração', 'modificação', 'aditivo', 'adendo', 'ajuste', 'atualização',
                'revisar', 'revisão', 'mudar termos'
            ],
            'cancelamento': [
                'cancelamento', 'rescisão', 'encerramento', 'finalizar', 'terminar',
                'desistência', 'cancelar', 'rescindir', 'encerrar'
            ],
            'pagamento': [
                'pagamento', 'fatura', 'nota fiscal', 'boleto', 'cobrança', 'recibo',
                'transferência', 'depósito', 'pagar', 'quitar'
            ],
            'duvida': [
                'dúvida', 'pergunta', 'esclarecimento', 'informação', 'como funciona',
                'gostaria de saber', 'poderia explicar', 'não entendi'
            ],
            'reclamacao': [
                'reclamação', 'problema', 'insatisfação', 'erro', 'falha', 'defeito',
                'não está funcionando', 'não recebi', 'atraso', 'descumprimento'
            ],
            'suporte': [
                'suporte', 'ajuda', 'assistência', 'auxílio', 'orientação', 'apoio',
                'como resolver', 'preciso de ajuda', 'não consigo'
            ]
        }
    
    def parse_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa um e-mail e extrai informações estruturadas.
        
        Args:
            email_data: Dados do e-mail
            
        Returns:
            Dict[str, Any]: E-mail com informações estruturadas
        """
        try:
            # Cria cópia do e-mail para não modificar o original
            parsed_email = email_data.copy()
            
            # Extrai texto do e-mail (corpo e anexos)
            all_text = self._extract_all_text(email_data)
            
            # Extrai entidades
            entities = self._extract_entities(all_text)
            parsed_email['entities'] = entities
            
            # Categoriza o e-mail
            category, confidence = self._categorize_email(email_data, all_text)
            parsed_email['category'] = category
            parsed_email['category_confidence'] = confidence
            
            # Determina prioridade
            priority = self._determine_priority(email_data, all_text, entities, category)
            parsed_email['priority'] = priority
            
            # Extrai metadados adicionais
            metadata = self._extract_metadata(email_data)
            parsed_email['metadata'] = metadata
            
            return parsed_email
        
        except Exception as e:
            logger.error(f"Erro ao analisar e-mail: {str(e)}")
            # Retorna o e-mail original com informações mínimas
            email_data['entities'] = {}
            email_data['category'] = 'desconhecido'
            email_data['category_confidence'] = 0.0
            email_data['priority'] = 'normal'
            email_data['metadata'] = {}
            email_data['parse_error'] = str(e)
            return email_data
    
    def _extract_all_text(self, email_data: Dict[str, Any]) -> str:
        """
        Extrai todo o texto relevante de um e-mail.
        
        Args:
            email_data: Dados do e-mail
            
        Returns:
            str: Todo o texto extraído
        """
        texts = []
        
        # Adiciona assunto
        subject = email_data.get('subject', '')
        if subject:
            texts.append(subject)
        
        # Adiciona corpo
        body = email_data.get('body', '')
        if body:
            texts.append(body)
        
        # Adiciona texto de anexos processados
        if 'processed_attachments' in email_data:
            for attachment in email_data['processed_attachments']:
                attachment_text = attachment.get('text', '')
                if attachment_text:
                    texts.append(attachment_text)
        
        # Combina todos os textos
        return "\n\n".join(texts)
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extrai entidades de um texto.
        
        Args:
            text: Texto a ser analisado
            
        Returns:
            Dict[str, List[str]]: Entidades extraídas
        """
        entities = {}
        
        # Aplica cada padrão
        for entity_type, patterns in self.patterns.items():
            matches = []
            
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Extrai o grupo capturado
                    value = match.group(1).strip()
                    
                    # Limpa o valor (remove pontuação no final, etc.)
                    value = re.sub(r'[.,;:]$', '', value)
                    
                    # Adiciona à lista de matches
                    if value and value not in matches:
                        matches.append(value)
            
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    def _categorize_email(self, email_data: Dict[str, Any], text: str) -> Tuple[str, float]:
        """
        Categoriza um e-mail com base em seu conteúdo.
        
        Args:
            email_data: Dados do e-mail
            text: Texto completo do e-mail
            
        Returns:
            Tuple[str, float]: Categoria e confiança
        """
        # Normaliza o texto (converte para minúsculas)
        normalized_text = text.lower()
        
        # Conta ocorrências de palavras-chave para cada categoria
        scores = {}
        
        for category, keywords in self.keywords.items():
            score = 0
            for keyword in keywords:
                # Conta ocorrências da palavra-chave
                count = normalized_text.count(keyword)
                score += count
            
            # Normaliza o score pelo número de palavras-chave
            if keywords:
                scores[category] = score / len(keywords)
            else:
                scores[category] = 0
        
        # Encontra a categoria com maior score
        if scores:
            max_category = max(scores.items(), key=lambda x: x[1])
            category = max_category[0]
            confidence = max_category[1]
            
            # Se a confiança for muito baixa, classifica como "outro"
            if confidence < 0.1:
                return "outro", confidence
            
            return category, confidence
        
        return "outro", 0.0
    
    def _determine_priority(self, email_data: Dict[str, Any], text: str, 
                           entities: Dict[str, List[str]], category: str) -> str:
        """
        Determina a prioridade de um e-mail.
        
        Args:
            email_data: Dados do e-mail
            text: Texto completo do e-mail
            entities: Entidades extraídas
            category: Categoria do e-mail
            
        Returns:
            str: Prioridade ('baixa', 'normal', 'alta', 'urgente')
        """
        # Palavras-chave de urgência
        urgency_keywords = [
            'urgente', 'emergência', 'imediato', 'crítico', 'prioritário',
            'prazo curto', 'vencendo', 'expirar', 'hoje', 'amanhã'
        ]
        
        # Verifica se há palavras de urgência no texto
        normalized_text = text.lower()
        urgency_count = sum(1 for keyword in urgency_keywords if keyword in normalized_text)
        
        # Categorias que geralmente têm prioridade mais alta
        high_priority_categories = ['cancelamento', 'reclamacao', 'pagamento']
        
        # Determina a prioridade base na categoria
        if category in high_priority_categories:
            base_priority = 'alta'
        else:
            base_priority = 'normal'
        
        # Ajusta com base nas palavras de urgência
        if urgency_count >= 3 or 'urgente' in normalized_text:
            return 'urgente'
        elif urgency_count >= 1 and base_priority == 'alta':
            return 'urgente'
        elif base_priority == 'alta':
            return 'alta'
        elif urgency_count >= 1:
            return 'alta'
        
        return base_priority
    
    def _extract_metadata(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai metadados adicionais de um e-mail.
        
        Args:
            email_data: Dados do e-mail
            
        Returns:
            Dict[str, Any]: Metadados extraídos
        """
        metadata = {}
        
        # Extrai informações do remetente
        from_addr = email_data.get('from', '')
        if from_addr:
            # Tenta extrair nome e e-mail
            match = re.search(r'([^<]+)<([^>]+)>', from_addr)
            if match:
                metadata['sender_name'] = match.group(1).strip()
                metadata['sender_email'] = match.group(2).strip()
            else:
                metadata['sender_email'] = from_addr.strip()
        
        # Extrai informações de data
        date = email_data.get('date', '')
        if date:
            metadata['email_date'] = date
        
        # Conta anexos
        attachments = email_data.get('attachments', [])
        metadata['attachment_count'] = len(attachments)
        
        # Extrai tipos de anexos
        if attachments:
            attachment_types = [attachment.get('content_type', 'unknown') for attachment in attachments]
            metadata['attachment_types'] = attachment_types
        
        return metadata

# Exemplo de uso
if __name__ == "__main__":
    # E-mail de exemplo
    email_data = {
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
        'processed_attachments': []
    }
    
    # Cria parser
    parser = EmailParser()
    
    # Analisa e-mail
    parsed_email = parser.parse_email(email_data)
    
    # Exibe resultados
    print(f"Categoria: {parsed_email['category']} (confiança: {parsed_email['category_confidence']:.2f})")
    print(f"Prioridade: {parsed_email['priority']}")
    print(f"Entidades:")
    for entity_type, values in parsed_email['entities'].items():
        print(f"  {entity_type}: {values}")
    print(f"Metadados: {parsed_email['metadata']}")
