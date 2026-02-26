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
```

---

## 🌐 Estrutura de URLs e Exemplos Práticos

Com base na estrutura do AutoRouter definida no seu código (`RouterController.py`) e na documentação, aqui estão exemplos práticos de como as URLs são formadas.

O padrão geral é: `{Protocolo}://{Dominio}:{Porta}/{Sufixo}/{Tabela}/{ID_ou_Rota}?{Filtros}`

### Cenário de Exemplo
*   **Servidor:** `http://localhost:5000`
*   **Tabela:** `Products`
*   **Sufixo Padrão:** `manager` (definido no código se não houver config)

### 1. Operações Básicas (CRUD)

| Ação | Método HTTP | URL Exemplo | Descrição |
| :--- | :--- | :--- | :--- |
| **Listar Tudo** | `GET` | `http://localhost:5000/manager/Products` | Retorna lista de produtos (padrão 20 itens). |
| **Buscar por ID** | `GET` | `http://localhost:5000/manager/Products/10` | Retorna apenas o produto com `RECID = 10`. |
| **Criar Novo** | `POST` | `http://localhost:5000/manager/Products` | Cria um produto (dados vão no corpo JSON). |
| **Atualizar** | `PATCH` | `http://localhost:5000/manager/Products/10` | Atualiza o produto 10 (dados parciais no corpo). |
| **Deletar** | `DELETE` | `http://localhost:5000/manager/Products/10` | Remove o produto 10. |

### 2. Filtros e Paginação (Query String)

Os filtros são adicionados após o `?` na URL. O `RouterController` interpreta sufixos como `_gt` (maior que), `_like` (contém), etc.

*   **Paginação:** `http://localhost:5000/manager/Products?page=2&limit=50` (Página 2, 50 itens por página)
*   **Preço maior que 100:** `http://localhost:5000/manager/Products?PRICE_gt=100`
*   **Nome contém "Gamer":** `http://localhost:5000/manager/Products?NAME_like=%Gamer%`
*   **Combinação (Preço < 50 E Ativo):** `http://localhost:5000/manager/Products?PRICE_lt=50&ACTIVE=1`

### 3. Rotas Customizadas
Se você definiu uma rota customizada no `CoreConfig` (ex: para limpar logs antigos), ela aparece como um "caminho" extra após a tabela.

*   **Configuração:** `{"route": "clear_old", ...}`
*   **URL:** `DELETE http://localhost:5000/manager/Logs/clear_old`
```

---

## 📝 Geração de Coleção Postman

O AutoRouter pode gerar automaticamente uma coleção Postman (v2.1) para todos os endpoints CRUD dinâmicos, facilitando a documentação e o teste da sua API.

### Como Gerar a Coleção

Você pode expor um endpoint na sua aplicação (ex: Flask, FastAPI) que chama o método `generate_postman_collection` do `AutoRouter`.

```python
# Exemplo em uma aplicação Flask
from flask import Flask, jsonify, request
from SQLManager.controller.RouterController import AutoRouter
from SQLManager.connection import database_connection
from SQLManager.CoreConfig import CoreConfig
import os

app = Flask(__name__)

# Configuração do CoreConfig e AutoRouter (assumindo que já foi feita na inicialização da app)
# Exemplo:
# CoreConfig.configure(db_server=os.getenv('DB_SERVER'), ...)
# CoreConfig.configure_router({"enable_dynamic_routes": True, "url_suffix": "api", ...})

# Inicialize a conexão com o banco de dados e o AutoRouter
# Em um ambiente de produção, a gestão de conexões e a inicialização
# do router seriam feitas de forma mais robusta (ex: com app context ou injeção de dependência).
db = database_connection() 
try:
    db.connect() # Tenta conectar, pode falhar se o DB não estiver disponível
except Exception as e:
    print(f"Aviso: Não foi possível conectar ao banco de dados para o exemplo: {e}")
    # Em um cenário real, você trataria isso de forma mais robusta.

router = AutoRouter(db)

@app.route('/generate-postman-collection', methods=['GET'])
def get_postman_collection():
    # A URL base será a da sua aplicação. O método generate_postman_collection
    # adicionará o sufixo configurado (ex: /api) automaticamente.
    # Ex: se a app roda em http://localhost:5000, a base_url será http://localhost:5000
    collection = router.generate_postman_collection(base_url=request.host_url.rstrip('/'))
    return jsonify(collection)

if __name__ == '__main__':
    # Exemplo de configuração mínima para rodar este snippet
    CoreConfig.configure(
        db_server=os.getenv('DB_SERVER', 'localhost'),
        db_database=os.getenv('DB_DATABASE', 'TestDB'),
        db_user=os.getenv('DB_USER', 'sa'),
        db_password=os.getenv('DB_PASSWORD', 'your_password')
    )
    CoreConfig.configure_router({
        "enable_dynamic_routes": True,
        "url_suffix": "api", # Define o sufixo para as URLs geradas no Postman
        "exclude_tables": ["SysLog"],
        "tables": {
            "Products": {"allowed_methods": ["GET", "POST", "PATCH", "DELETE"]}
        }
    })
    app.run(debug=True, port=5000)
```

### Configuração do Sufixo da URL

O sufixo para as URLs geradas na coleção Postman é definido na configuração do `CoreConfig` através da chave `url_suffix`.

-   **Padrão:** Se `url_suffix` não for especificado, o valor padrão será `'manager'`.
-   **Customizado:** Se você configurar `url_suffix: 'api/v1'`, as URLs na coleção serão `http://localhost:5000/api/v1/{Tabela}`.

**Exemplo de Configuração:**
```python
from SQLManager import CoreConfig

CoreConfig.configure_router({
    "enable_dynamic_routes": True,
    "url_suffix": "api", # As URLs no Postman serão /api/{Tabela}
    # ... outras configurações
})
```

---

## 🔍 Exemplo de Verificação de URL (Debug)

Para verificar como o `AutoRouter` processa uma URL sem precisar subir um servidor web, você pode chamar diretamente o método `handle_request`.

```python
from SQLManager.controller.RouterController import AutoRouter
from SQLManager.CoreConfig import CoreConfig
from unittest.mock import MagicMock

# 1. Configuração (Simulada)
CoreConfig.reset()
CoreConfig.configure_router({
    "enable_dynamic_routes": True,
    "url_suffix": "api",
    "tables": {
        "Products": {
            "allowed_methods": ["GET", "POST", "DELETE"]
        }
    }
})

# 2. Inicialização (Mockando o banco para não precisar de conexão real neste teste)
mock_db = MagicMock()
router = AutoRouter(mock_db)

# --- TESTES DE VERIFICAÇÃO ---

print("=== Teste 1: Listar Produtos (GET /Products?page=1&limit=5) ===")
# Simula: GET http://localhost/api/Products?page=1&limit=5
response = router.handle_request(
    method="GET",
    table_name="Products",
    path_parts=[], 
    query_params={"page": "1", "limit": "5"}
)
print(f"Status: {response.get('status')}")

print("\n=== Teste 2: Buscar por ID (GET /Products/123) ===")
# Simula: GET http://localhost/api/Products/123
response = router.handle_request(
    method="GET",
    table_name="Products",
    path_parts=["123"]
)
print(f"Status: {response.get('status')}")
``` 