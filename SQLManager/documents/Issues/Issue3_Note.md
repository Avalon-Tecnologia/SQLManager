# Issues [#3-AutoRouterSystem](https://github.com/nickzsd/SQLManager/issues/3) - SQLManager
**Versão:** 4.0 | **Última Atualização:** 27/02/2026

O **AutoRouter** é um módulo inteligente do SQLManager que transforma automaticamente suas classes de Tabela (`TableController`) em endpoints de API RESTful **prontos para uso**.

Ele elimina a necessidade de criar controllers, rotas e serviços manuais para operações CRUD (Create, Read, Update, Delete) padrão, permitindo que você exponha seu banco de dados de forma segura e imediata.

## 🎯 Objetivo e Benefícios

- **Zero Boilerplate:** Crie a tabela no banco, rode o gerador de modelos, e a rota já existe automaticamente.
- **Registro Automático (Flask):** Passe o objeto `app` Flask e todas as rotas são criadas instantaneamente.
- **Padronização:** Todas as respostas seguem o mesmo formato JSON, com códigos HTTP corretos (200, 201, 400, 404, 500).
- **Segurança:** Validação automática de tipos de dados (EDTs) e Enums antes de tocar no banco.
- **Filtros Poderosos:** Suporte nativo a filtros complexos via URL (maior que, contém, diferente, etc.).
- **Documentação Automática:** Gera coleção Postman completa com todos os endpoints.

## ✅ Quando Usar vs. ❌ Quando NÃO Usar

| ✅ Use o AutoRouter quando... | ❌ NÃO use o AutoRouter quando... |
| :--- | :--- |
| Precisa de CRUD padrão (Listar, Ler, Criar, Deletar). | A operação exige orquestração complexa de múltiplos serviços. |
| Tabelas de cadastro, configurações, logs. | Existem regras de negócio muito específicas que não cabem no `validate_write` da tabela. |
| Prototipagem rápida de API e Front-end. | Relatórios analíticos pesados (BI) que exigem queries otimizadas manualmente. |
| Microserviços RESTful simples. | Operações que envolvem múltiplas tabelas com transações complexas. |

---

## 🚀 Inicialização e Configuração

### Passo 1: Configurar o CoreConfig

O AutoRouter é **OPCIONAL**. Para ativá-lo, você deve configurar o `CoreConfig` na inicialização da sua aplicação.

**Exemplo Completo de Configuração:**

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

### Passo 2: Inicializar o AutoRouter

O AutoRouter agora suporta **dois modos de operação**:

#### **Modo 1: Flask com Registro Automático (Recomendado)**

No modo Flask, todas as rotas são criadas automaticamente ao instanciar o AutoRouter:

```python
from flask import Flask
from SQLManager.connection import database_connection
from SQLManager.controller.RouterController import AutoRouter

app = Flask(__name__)

# Conecta ao banco de dados
db = database_connection()

# Cria o AutoRouter e passa o app Flask
# As rotas são registradas AUTOMATICAMENTE!
router = AutoRouter(db, app=app)

@app.route('/')
def index():
    routes = router.get_registered_routes()
    return {
        "message": "SQLManager API está ativa!",
        "tables": list(routes.keys()),
        "total_routes": sum(len(r) for r in routes.values())
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**O que acontece:**
- ✅ Todas as tabelas são descobertas automaticamente
- ✅ Rotas CRUD são criadas para cada tabela permitida
- ✅ Rotas customizadas (do CoreConfig) são registradas
- ✅ Você pode rodar `app.run()` imediatamente

#### **Modo 2: Manual (Para frameworks customizados)**

Se você não usa Flask ou quer controle total, pode processar requisições manualmente:

```python
from SQLManager.connection import database_connection
from SQLManager.controller.RouterController import AutoRouter

db = database_connection()
router = AutoRouter(db)  # SEM passar o app

# Processa requisição manualmente
response = router.handle_request(
    method='GET',
    table_name='Products',
    path_parts=['1'],  # ID ou rota customizada
    query_params={'page': '1', 'limit': '10'},
    body={}
)

print(response)
# {"status": 200, "data": {...}, "meta": {...}}
```

---

## 🛣️ Rotas Criadas Automaticamente

Quando você inicializa o AutoRouter com um app Flask, as seguintes rotas são criadas **automaticamente** para cada tabela:

Assumindo:
- **Servidor:** `http://localhost:5000`
- **Sufixo:** `manager` (configurado no CoreConfig via `url_suffix`)
- **Tabela:** `Products`

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

## Metodologia e Arquitetura

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

## Testes Unitários

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

## Estrutura de URLs e Exemplos Práticos

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

## 📦 Geração de Coleção Postman

O AutoRouter pode gerar automaticamente uma **coleção Postman (v2.1)** completa com todos os endpoints disponíveis, incluindo rotas customizadas.

### Para Que Serve?

- 📝 **Documentação automática** da sua API
- 🧪 **Testes rápidos** sem precisar escrever código
- 👥 **Compartilhamento** com equipe de front-end ou QA
- 🔄 **Atualização instantânea** quando você adiciona novas tabelas

### Como Gerar a Coleção

**Opção 1: Via Código Python (Recomendado)**

```python
from SQLManager.connection import database_connection
from SQLManager.controller.RouterController import AutoRouter
import json

# Inicializa o router
db = database_connection()
router = AutoRouter(db)

# Gera a coleção Postman
collection = router.generate_collection(
    base_url="http://localhost:5000",
    collection_name="SQLManager API - Meu Projeto"
)

# Salva em arquivo JSON
with open('postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print("✅ Coleção Postman gerada: postman_collection.json")
print(f"📊 Total de tabelas: {len(collection['item'])}")
```

**Opção 2: Via Endpoint Flask**

```python
from flask import jsonify, request

@app.route('/api/postman-collection', methods=['GET'])
def get_postman_collection():
    """Endpoint para baixar a coleção Postman"""
    collection = router.generate_collection(
        base_url=request.host_url.rstrip('/'),
        collection_name="SQLManager API"
    )
    return jsonify(collection)
```

Acesse: `http://localhost:5000/api/postman-collection` e salve o JSON.

### O Que É Gerado?

A coleção Postman inclui **todas as rotas** por tabela:

```json
{
  "info": {
    "name": "SQLManager API - Meu Projeto",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Products",
      "item": [
        {"name": "List Products", "request": {"method": "GET", "url": "http://localhost:5000/manager/Products?page=1&limit=10"}},
        {"name": "Get Products by ID", "request": {"method": "GET", "url": "http://localhost:5000/manager/Products/1"}},
        {"name": "Create Products", "request": {"method": "POST", "url": "...", "body": {...}}},
        {"name": "Update Products", "request": {"method": "PATCH", "url": "..."}},
        {"name": "Delete Products", "request": {"method": "DELETE", "url": "..."}},
        {"name": "Get Products - active", "request": {"method": "GET", "url": ".../active"}}
      ]
    }
  ]
}
```

### Importando no Postman

1. Abra o Postman
2. Clique em **Import**
3. Selecione o arquivo `postman_collection.json`
4. ✅ Todas as rotas estarão prontas para teste!

### Configuração do Sufixo da URL

O sufixo das URLs na coleção é definido no `CoreConfig`:

```python
CoreConfig.configure_router({
    "url_suffix": "api/v1"  # URLs serão /api/v1/{Tabela}
})
```

- **Padrão:** `manager` → URLs: `/manager/Products`
- **Customizado:** `api/v1` → URLs: `/api/v1/Products`

---

## 🔍 Listando Rotas Registradas

Para ver todas as rotas que foram registradas automaticamente, use o método `get_registered_routes()`:

```python
from flask import Flask
from SQLManager.connection import database_connection
from SQLManager.controller.RouterController import AutoRouter

app = Flask(__name__)
db = database_connection()
router = AutoRouter(db, app=app)

# Obtém informações sobre todas as rotas
routes_info = router.get_registered_routes()

print("\n📋 Rotas Registradas Automaticamente:")
print("=" * 80)
for table_name, routes in routes_info.items():
    print(f"\n📦 Tabela: {table_name}")
    for route in routes:
        print(f"  {route['method']:7} {route['endpoint']:45} → {route['description']}")

print(f"\n✅ Total: {sum(len(r) for r in routes_info.values())} rotas em {len(routes_info)} tabelas")
```

**Saída exemplo:**
```
📋 Rotas Registradas Automaticamente:
================================================================================

📦 Tabela: Products
  GET     /manager/Products                             → Listar Products
  GET     /manager/Products/{id}                        → Obter Products por ID
  POST    /manager/Products                             → Criar Products
  PATCH   /manager/Products/{id}                        → Atualizar Products
  DELETE  /manager/Products/{id}                        → Deletar Products
  GET     /manager/Products/active                      → Rota customizada: active

📦 Tabela: Customers
  GET     /manager/Customers                            → Listar Customers
  GET     /manager/Customers/{id}                       → Obter Customers por ID

✅ Total: 8 rotas em 2 tabelas
```

---

## 🧪 Testando Rotas (Debug)

Para verificar como o `AutoRouter` processa requisições sem subir um servidor:

```python
from SQLManager.controller.RouterController import AutoRouter
from SQLManager.connection import database_connection

db = database_connection()
router = AutoRouter(db)  # Modo manual

# Teste 1: Listar produtos com paginação
response = router.handle_request(
    method="GET",
    table_name="Products",
    path_parts=[],
    query_params={"page": "1", "limit": "5"}
)
print(f"Status: {response['status']}")
print(f"Dados: {response.get('data', [])}")

# Teste 2: Buscar por ID
response = router.handle_request(
    method="GET",
    table_name="Products",
    path_parts=["123"]
)
print(f"Status: {response['status']}")

# Teste 3: Criar produto
response = router.handle_request(
    method="POST",
    table_name="Products",
    body={"NAME": "Produto Teste", "PRICE": 99.90}
)
print(f"Status: {response['status']}")
print(f"RECID criado: {response.get('data', {}).get('RECID')}")
``` 

---

## Refatoração do Decorator `_pre_handle` (v4.0 - 27/02/2026)

### Motivação
Na versão inicial, o decorator `_pre_handle` usava uma lógica manual para extrair argumentos (`args[0]`, `kwargs[...]`), o que era frágil e não type-safe. A refatoração implementou o uso de `inspect.signature` do Python para tornar o mapeamento de argumentos robusto e confiável.

### O Que Mudou

**Antes (v1.0):**
```python
def _pre_handle(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        def get_args(_args: str):
            args_info = None
            if _args in kwargs:
                args_info = kwargs[_args]
            else:
                args_info = args[0] if len(args) > 0 else None
            return args_info

        method = get_args('method')
        table_name = get_args('table_name')
        # ... validações ...
        return func(*args, **kwargs)
    return wrapper
```

**Problemas:**
- ❌ Não funcionava corretamente com `self` ausente
- ❌ Mapeamento frágil de argumentos posicionais vs nomeados
- ❌ Não validava assinatura da função
- ❌ Difícil de manter e estender

**Depois (v4.0):**
```python
def _pre_handle(func):
    sig = inspect.signature(func)  # Captura assinatura ANTES
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Mapeia argumentos usando a assinatura
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        # Extrai com segurança
        self = bound.arguments.get('self')
        method = bound.arguments.get('method', '').upper()
        table_name = bound.arguments.get('table_name', '')
        
        # ... validações usando self ...
        
        # Injeta objetos preparados
        kwargs['_table'] = table
        kwargs['_table_config'] = table_config
        
        return func(*args, **kwargs)
    return wrapper
```

**Benefícios:**
- ✅ Type-safe: valida assinatura automaticamente
- ✅ Funciona com argumentos nomeados e posicionais
- ✅ Extração robusta de `self` e outros parâmetros
- ✅ Injeção de dependências (`_table`, `_table_config`)
- ✅ Fácil de testar e manter

### Exemplo de Uso

O decorator valida e prepara tudo antes de chamar `handle_request`:

```python
# Chamada com argumentos nomeados
response = router.handle_request(
    method='GET',
    table_name='Products',
    path_parts=['123']
)

# Chamada com argumentos posicionais
response = router.handle_request('GET', 'Products', ['123'])

# Ambos funcionam! O decorator mapeia corretamente usando inspect.signature
```

### Testes

A refatoração foi validada com testes unitários completos em [`test_AutoRouter.py`](../../tests/test_AutoRouter.py):

```python
def test_decorator_maps_arguments_correctly(self):
    """Valida que inspect.signature mapeia args/kwargs"""
    response = self.router.handle_request(method="GET", table_name="Products")
    self.assertIsInstance(response, dict)
    
def test_decorator_with_positional_arguments(self):
    """Valida argumentos posicionais"""
    response = self.router.handle_request("GET", "Products", [], {}, {})
    self.assertIn("status", response)
```

### Arquivos Modificados
- `SQLManager/controller/RouterController.py` (linhas 44-107, 110-153, 182-221)
- `SQLManager/tests/test_AutoRouter.py` (testes completos do decorator)
- `SQLManager/__init__.py` (remoção de `StartRoutes()` inexistente)

---

## 🆕 Atualização v4.0 - Registro Automático Flask (27/02/2026)

### Mudanças Implementadas

#### 1. **Novo Parâmetro `app` no Construtor**
```python
# Antes (v3.0)
router = AutoRouter(db)

# Agora (v4.0)
router = AutoRouter(db, app=app)  # Rotas criadas automaticamente!
```

#### 2. **Método `_register_routes()`**
Registra automaticamente todos os endpoints Flask:
- Lista todos as tabelas disponíveis via `_discover_tables()`
- Cria rotas para cada método HTTP permitido (GET, POST, PATCH, DELETE)
- Registra rotas customizadas do CoreConfig
- Usa closures para evitar problemas de binding tardio

#### 3. **Método `get_registered_routes()`**
Retorna dicionário com informações de todas as rotas:
```python
routes = router.get_registered_routes()
# {
#   "Products": [
#     {"method": "GET", "endpoint": "/manager/Products", "description": "Listar Products"},
#     ...
#   ]
# }
```

#### 4. **Método `generate_collection()` Melhorado**
Agora gera **coleção Postman completa**:
- ✅ Todas as rotas por tabela (não apenas uma)
- ✅ Rotas customizadas (GET/DELETE)
- ✅ Estrutura Postman v2.1 completa
- ✅ Informações de metadados

### Arquivos Criados
- `SQLManager/controller/example_autorouter_usage.py` - Exemplos de uso completos
- `SQLManager/documents/Issues/Issue3_AutoRouter_Update.md` - Documentação da atualização

---

## 📚 Referências e Exemplos

### Exemplo Completo de Aplicação Flask

Veja o arquivo [`example_autorouter_usage.py`](../../controller/example_autorouter_usage.py) para exemplos completos de:
- Inicialização com Flask
- Modo manual
- Geração de coleção Postman
- Listagem de rotas
- Configuração avançada

### Testes Unitários

Veja [`test_AutoRouter.py`](../../tests/test_AutoRouter.py) para exemplos de:
- Testes de validação
- Mock de banco de dados
- Testes de rotas CRUD
- Testes de decorator

---

## 🎓 Autores e Histórico

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 25/02/2026 | Matheus | Implementação inicial do AutoRouter |
| 2.0 | 26/02/2026 | Nicolas Santos | Refatoração do decorator `_pre_handle` |
| 3.0 | 27/02/2026 | Nicolas Santos | Cache de classes e field maps |
| 4.0 | 27/02/2026 | Matheus | Registro automático Flask + generate_collection melhorado | 