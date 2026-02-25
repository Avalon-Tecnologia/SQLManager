# Issues [#3-AutoRouterSystem](https://github.com/nickzsd/SQLManager/issues/3) - SQLManager

O **AutoRouter** é um módulo inteligente do SQLManager que transforma automaticamente suas classes de Tabela (`TableController`) em endpoints de API RESTful.

Ele elimina a necessidade de criar controllers, rotas e serviços manuais para operações CRUD (Create, Read, Update, Delete) padrão, permitindo que você exponha seu banco de dados de forma segura e imediata.

## 🎯 Objetivo e Benefícios

- **Zero Boilerplate:** Crie a tabela no banco, rode o gerador de modelos, e a rota já existe.
- **Padronização:** Todas as respostas seguem o mesmo formato JSON, com códigos HTTP corretos (200, 201, 400, 404, 500).
- **Segurança:** Validação automática de tipos de dados (EDTs) e Enums antes de tocar no banco.
- **Filtros Poderosos:** Suporte nativo a filtros complexos via URL (maior que, contém, diferente, etc.).

## ⚠️ Quando Usar vs. Quando NÃO Usar

| Use o AutoRouter quando... | NÃO use o AutoRouter quando... |
| :--- | :--- |
| Precisa de CRUD padrão (Listar, Ler, Criar, Deletar). | A operação exige orquestração complexa de múltiplos serviços. |
| Tabelas de cadastro, configurações, logs. | Existem regras de negócio muito específicas que não cabem no `validate_write` da tabela. |
| Prototipagem rápida de API e Front-end. | Relatórios analíticos pesados (BI) que exigem queries otimizadas manualmente. |

---

## ⚙️ Ativação e Configuração

O AutoRouter é **OPCIONAL**. Para ativá-lo, você deve configurar o `CoreConfig` na inicialização da sua aplicação.

### Exemplo Completo de Configuração

```python
from SQLManager import CoreConfig

router_config = {
    # [OBRIGATÓRIO] Ativa o sistema de rotas
    "enable_dynamic_routes": True,

    # Tabelas que NÃO devem ter rotas expostas (ex: tabelas de sistema, senhas)
    "exclude_tables": ["SysLog", "UserPasswords", "ConfigSecrets"],

    # Configurações específicas por tabela
    "tables": {
        "Products": {
            # Define quais métodos HTTP são aceitos para esta tabela
            "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
            
            # Configuração de Deleção Lógica (Opcional)
            # Se configurado, o DELETE fará um UPDATE no campo definido ao invés de apagar o registro.
            "delete_behavior": {
                "mode": "logical",       
                "field": "IS_DELETED",   
                "value": 1               
            }
        },
        "ReadOnlyTable": {
            "allowed_methods": ["GET"] # Apenas leitura
        },
        "Logs": {
            # Rotas customizadas de DELETE
            "custom_delete": [
                { "route": "clear_old", "where": "DATE < '2023-01-01'" }
            ]
        }
    }
}

# Aplica a configuração
CoreConfig.configure_router(router_config)
```

---

## 🛣️ Endpoints Disponíveis

Assumindo que sua aplicação rode em `http://localhost:8000` e o prefixo seja `/api`.

### 1. Listagem e Filtros (GET)
**Rota:** `GET /api/{Tabela}`

Retorna uma lista de registros. Suporta paginação e filtros avançados via Query String.

**Parâmetros de Paginação:**
- `page`: Número da página (Padrão: 1)
- `limit`: Registros por página (Padrão: 20)

**Filtros Avançados:**
O AutoRouter suporta sufixos nos nomes dos campos para operações de comparação:

| Sufixo | Operador SQL | Exemplo URL | Descrição |
| :--- | :--- | :--- | :--- |
| `(nenhum)` | `=` | `?CATEGORY=Eletronicos` | Igualdade exata. |
| `_gt` | `>` | `?PRICE_gt=100` | Maior que 100. |
| `_gte` | `>=` | `?PRICE_gte=100` | Maior ou igual a 100. |
| `_lt` | `<` | `?STOCK_lt=10` | Menor que 10. |
| `_lte` | `<=` | `?DATE_lte=2023-12-31` | Menor ou igual a data. |
| `_neq` | `!=` | `?STATUS_neq=Inativo` | Diferente de "Inativo". |
| `_like` | `LIKE` | `?NAME_like=%Mouse%` | Busca textual (contém). |

**Exemplo de Requisição:**
```http
GET /api/Products?page=1&limit=10&PRICE_gte=50&NAME_like=%Gamer%
```

### 2. Busca por ID (GET)
**Rota:** `GET /api/{Tabela}/{id}`

Retorna um único registro baseado no `RECID`.

**Exemplo:** `GET /api/Products/123`

### 3. Criação (POST)
**Rota:** `POST /api/{Tabela}`

Cria um novo registro. O corpo da requisição deve ser um JSON com os campos da tabela.

**Validação Automática:**
- O AutoRouter verifica se os campos existem na tabela.
- Valida os tipos de dados (EDTs).
- Valida Enums (se o valor enviado é válido).

**Exemplo Body:**
```json
{
    "NAME": "Teclado Mecânico",
    "PRICE": 250.00,
    "CATEGORY": "Periféricos"
}
```

### 4. Atualização Parcial (PATCH)
**Rota:** `PATCH /api/{Tabela}/{id}`

Atualiza apenas os campos enviados no JSON. Campos não enviados permanecem inalterados.

**Exemplo Body:**
```json
{
    "PRICE": 230.00
}
```

### 5. Deleção (DELETE)
**Rota:** `DELETE /api/{Tabela}/{id}`

Remove o registro. Se `delete_behavior` estiver configurado como `logical`, fará apenas um update no campo de flag.

**Rota Customizada:** `DELETE /api/{Tabela}/{custom_route}`
Executa deleção em massa baseada em configuração.

**Exemplo:** `DELETE /api/Logs/clear_old` (Remove logs antigos conforme config)

---

## 📡 Formato de Resposta

O AutoRouter sempre retorna um JSON padronizado.

### Sucesso (200 OK / 201 Created)
```json
{
  "status": 200,
  "data": [ ... ],  // Lista ou Objeto
  "meta": {         // Apenas em listagens
    "page": 1,
    "limit": 20,
    "count": 15
  },
  "message": "Updated successfully" // Em operações de escrita
}
```

### Erro (4xx / 5xx)
```json
{
  "status": 400,
  "error": "Descrição do erro (ex: Invalid Field)",
  "message": "Detalhes técnicos ou mensagem amigável"
}
```

---

## 🧠 Metodologia e Arquitetura

Com base na análise do código fonte e da documentação fornecida, o **AutoRouter** utiliza a metodologia de **Roteamento Dinâmico** (Dynamic Routing) fundamentada em **Reflexão** (Reflection/Introspection) e **Convenção sobre Configuração** (Convention over Configuration).

Aqui está o detalhamento técnico dessa abordagem:

1. **Roteamento Dinâmico:**
   Ao contrário de frameworks tradicionais onde cada rota precisa ser declarada manualmente (ex: `@app.route('/products')`), o AutoRouter interpreta a URL em tempo de execução. Ele analisa o caminho `/api/{Tabela}/{ID}` para decidir qual classe carregar e qual operação executar.

2. **Reflexão (Reflection):**
   O sistema utiliza capacidades de introspecção do Python (como `importlib`, `getattr`, `setattr` e `dir`) para:
   - Importar dinamicamente a classe da tabela (`TableController`) baseada no nome passado na URL.
   - Mapear os campos do JSON recebido para os atributos da classe sem conhecê-los previamente.
   - Inspecionar a estrutura da classe para gerar o mapa de campos (`_get_field_map`).

3. **Convenção sobre Configuração:**
   O sistema assume que a estrutura da URL corresponde à estrutura das classes do projeto (ex: URL `/Products` busca a classe `Products`). Isso elimina a necessidade de arquivos de configuração extensos ("Zero Boilerplate"), pois a simples existência da classe já habilita a rota (desde que não esteja na lista de exclusão).

4. **Padrão Front Controller:**
   O método `handle_request` atua como um controlador frontal único que recebe todas as requisições e as despacha para a lógica apropriada, centralizando o tratamento de erros e a padronização das respostas.

---

## � Testes Unitários

Abaixo está um exemplo completo de como testar o `AutoRouter` utilizando `unittest` e `mock`. Este teste cobre cenários de sucesso (CRUD) e tratamento de erros (404, 405, etc.), simulando o comportamento do banco de dados.

```python
''' [BEGIN CODE] Project: SQLManager / made by: {Matheus} / created: {25/02/2026} '''

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adiciona o diretório raiz ao path para permitir importação dos módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.controller.AutoRouter import AutoRouter
from SQLManager.CoreConfig import CoreConfig
from SQLManager.controller.TableController import TableController

class TestAutoRouter(unittest.TestCase):
    
    def setUp(self):
        # Reseta configurações antes de cada teste
        CoreConfig.reset()
        
        # Mock da conexão com banco de dados
        self.mock_db = MagicMock()
        
        # Configuração padrão para os testes
        self.router_config = {
            "enable_dynamic_routes": True,
            "exclude_tables": ["SecretTable"],
            "tables": {
                "Products": {
                    "allowed_methods": ["GET", "POST", "PATCH", "DELETE"]
                }
            }
        }
        CoreConfig.configure_router(self.router_config)
        
        # Instancia o Router
        self.router = AutoRouter(self.mock_db)

    def test_router_disabled(self):
        """Testa se o router retorna 404 quando desabilitado"""
        print("\n[TESTE] Router Desabilitado")
        CoreConfig.configure_router({"enable_dynamic_routes": False})
        # Reinstancia para pegar nova config
        router = AutoRouter(self.mock_db)
        
        response = router.handle_request("GET", "Products")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 404)
        self.assertIn("disabled", response["error"])

    def test_table_excluded(self):
        """Testa acesso a tabela excluída/restrita"""
        print("\n[TESTE] Tabela Excluída")
        response = self.router.handle_request("GET", "SecretTable")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 404)
        self.assertIn("restricted", response["error"])

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    def test_table_not_found(self, mock_get_class):
        """Testa acesso a tabela inexistente"""
        print("\n[TESTE] Tabela Não Encontrada")
        mock_get_class.return_value = None
        
        response = self.router.handle_request("GET", "NonExistent")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 404)
        self.assertIn("not found", response["error"])