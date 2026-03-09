# Issues [#5-Relation System](https://github.com/nickzsd/SQLManager/issues/5) - SQLManager

## O que são Relations?

Relations são relacionamentos automáticos entre tabelas que permitem:
- **Auto-população via JOIN**: Os dados relacionados são carregados automaticamente
- **Records separados**: Cada relation tem seus próprios records
- **Acesso tipado**: Acesse dados relacionados através de `table.relations["nome"]`
- **Filtros específicos**: Adicione WHERE às relations para rotas automáticas

## Como usar

### 1. Definir Relations na Tabela

```python
class PlanMensalities(TableController):
    def __init__(self, db):
        super().__init__(db, "PlanMensalities")
        self.PLANID = EDTController("int", DataType.Number)
        self.AMOUNT = EDTController("float", DataType.Float)

class SellerPlansTable(TableController):
    def __init__(self, db):
        super().__init__(db, "SellerPlansTable")
        self.PLANID = EDTController("int", DataType.Number)
        self.NAME = EDTController("str", DataType.String)
        
        # Define relations (inicialmente vazio)
        self.relations = {}
    
    def setup_relations(self):
        '''Configura relations após inicialização'''
        temp_mens = PlanMensalities(self.db)
        
        self.relations = {
            "mensalities": self.new_Relation(PlanMensalities)
                              .on(self.PLANID, temp_mens.PLANID)
                              .join_type_as('LEFT')  # Opcional, padrão é LEFT
        }
```

### 2. Usar Relations em SELECT

```python
# Criar instância e configurar relations
seller_plans = SellerPlansTable(trs)
seller_plans.setup_relations()

# SELECT com relation - Auto-executa e popula
seller_plans.select().with_relations("mensalities").where(seller_plans.PLANID == 5)

# Acessar dados do plano (tabela principal)
print(f"Plano: {seller_plans.NAME}")
print(f"Total records: {len(seller_plans.records)}")

# Acessar dados da relation
mensalities = seller_plans.relations["mensalities"]
print(f"Total mensalidades: {len(mensalities.records)}")

# Iterar pelos records da relation
for record in mensalities.records:
    print(f"AMOUNT: {record['AMOUNT']}")

# Acessar através da instância da tabela relacionada
table_instance = mensalities.get_instance()
print(f"AMOUNT atual: {table_instance.AMOUNT}")
```

### 3. Múltiplas Relations

```python
class OrderTable(TableController):
    def __init__(self, db):
        super().__init__(db, "Orders")
        # ... campos ...
        self.relations = {}
    
    def setup_relations(self):
        temp_items = OrderItems(self.db)
        temp_customer = Customers(self.db)
        
        self.relations = {
            "items": self.new_Relation(OrderItems)
                        .on(self.ORDERID, temp_items.ORDERID),
            "customer": self.new_Relation(Customers)
                           .on(self.CUSTOMERID, temp_customer.CUSTOMERID)
        }

# Usar múltiplas relations
order.select().with_relations("items", "customer").where(order.ORDERID == 10)
```

### 4. Filtros nas Relations (para Rotas Automáticas)

```python
def setup_relations(self):
    temp_mens = PlanMensalities(self.db)
    
    self.relations = {
        # Apenas mensalidades ativas
        "active_mensalities": self.new_Relation(PlanMensalities)
                                 .on(self.PLANID, temp_mens.PLANID)
                                 .where(temp_mens.ACTIVE == True),
        
        # Apenas mensalidades do ano atual
        "current_year": self.new_Relation(PlanMensalities)
                           .on(self.PLANID, temp_mens.PLANID)
                           .where(temp_mens.YEAR == 2026)
    }
```

## API Reference

### RelationManager

#### `.on(source_field, target_field)`
Define os campos de relacionamento entre tabelas.

```python
.on(self.PLANID, other_table.PLANID)
```

#### `.join_type_as(join_type)`
Define o tipo de JOIN (padrão: LEFT).

```python
.join_type_as('INNER')  # ou 'LEFT', 'RIGHT'
```

#### `.where(condition)`
Adiciona filtros específicos para esta relation.

```python
.where(table.ACTIVE == True)
```

#### `.get_instance()`
Retorna a instância da tabela relacionada.

```python
mensalities_table = relation.get_instance()
print(mensalities_table.AMOUNT)
```

#### `.records`
Lista de records populados pela relation.

```python
for record in relation.records:
    print(record)
```

### SelectManager

#### `.with_relations(*relation_names)`
Inclui relations automáticas no SELECT.

```python
table.select().with_relations("mensalities", "items")
```

## Comparação: Antes vs Depois

### Antes (JOIN manual)

```python
with database.transaction() as trs:
    seller_plans = SellerPlansTable(trs)
    mensalities = PlanMensalities(trs)
    
    # JOIN manual
    seller_plans.select().join(mensalities).on(
        seller_plans.PLANID == mensalities.PLANID
    ).execute()
    
    # Acessar dados
    print(seller_plans.records)
    print(mensalities.records)  # Precisa da instância separada
```

### Depois (Relations automáticas)

```python
with database.transaction() as trs:
    seller_plans = SellerPlansTable(trs)
    seller_plans.setup_relations()
    
    # SELECT com relation automática
    seller_plans.select().with_relations("mensalities").where(
        seller_plans.PLANID == 5
    )
    
    # Acessar dados
    print(seller_plans.records)
    print(seller_plans.relations["mensalities"].records)  # Tudo em um lugar!
```

## Vantagens

1. **Organização**: Todas as relations em um único dicionário
2. **Auto-população**: Records são automaticamente separados e populados
3. **Tipagem**: Acesso via nomes semânticos (`"mensalities"` ao invés de variáveis separadas)
4. **Filtros embutidos**: WHERE nas relations para filtros específicos
5. **Reutilização**: Defina uma vez, use em todas as queries
6. **Rotas automáticas**: Ideal para sistemas de rotas que precisam carregar dados relacionados

## Notas Importantes

- **Classes vs Instâncias**: `new_Relation()` recebe a CLASSE, não a instância
- **Setup**: Use um método `setup_relations()` para evitar problemas de ordem de definição
- **Performance**: Relations usam JOINs, portanto têm a mesma performance de JOINs manuais
- **Compatibilidade**: Você ainda pode usar `.join()` manualmente se preferir

## Exemplos Práticos

### Exemplo 1: E-commerce

```python
class Product(TableController):
    def setup_relations(self):
        self.relations = {
            "reviews": self.new_Relation(Reviews).on(self.ID, Reviews.PRODUCTID),
            "category": self.new_Relation(Category).on(self.CATEGORYID, Category.ID),
            "stock": self.new_Relation(Stock).on(self.ID, Stock.PRODUCTID)
        }

# Buscar produto com todas as informações
product.select().with_relations("reviews", "category", "stock").where(product.ID == 100)
```

### Exemplo 2: CRM

```python
class Customer(TableController):
    def setup_relations(self):
        self.relations = {
            "orders": self.new_Relation(Orders).on(self.ID, Orders.CUSTOMERID),
            "addresses": self.new_Relation(Addresses).on(self.ID, Addresses.CUSTOMERID),
            "contacts": self.new_Relation(Contacts).on(self.ID, Contacts.CUSTOMERID)
        }

# Buscar cliente completo
customer.select().with_relations("orders", "addresses").where(customer.EMAIL == "test@email.com")

# Acessar endereços
for address in customer.relations["addresses"].records:
    print(f"{address['STREET']}, {address['CITY']}")
```

## Integração com AutoRouter

O AutoRouter detecta e serializa automaticamente as relations definidas nas tabelas, retornando JSON estruturado.

### Response Automático com Relations

Quando uma tabela tem relations definidas, o AutoRouter:
1. Carrega automaticamente via `with_relations()`
2. Serializa os dados relacionados no JSON de resposta
3. Retorna estrutura aninhada com chave `relations`

**Exemplo de Response:**

```json
{
  "status": 200,
  "data": {
    "RECID": 1,
    "PLANID": "PLN0003",
    "NAME": "Plano Premium",
    "DESCRIPTION": "Plano com recursos completos",
    "relations": {
      "mensalities": [
        {
          "RECID": 10,
          "PLANID": "PLN0003",
          "AMOUNT": 99.90,
          "CREATEDATETIME": "2026-01-01T00:00:00"
        },
        {
          "RECID": 11,
          "PLANID": "PLN0003",
          "AMOUNT": 99.90,
          "CREATEDATETIME": "2026-02-01T00:00:00"
        }
      ]
    }
  }
}
```

### Exemplo Completo: AutoRouter + Relations

```python
# Definição da Tabela
class PlanMensalities(TableController):
    def __init__(self, db):
        super().__init__(db, "PlanMensalities")
        self.RECID = Recid()
        self.PLANID = EDTController("str", DataType.String)
        self.AMOUNT = EDTController("float", DataType.Float)

class SellerPlansTable(TableController):
    def __init__(self, db):
        super().__init__(db, "SellerPlansTable")
        self.RECID = Recid()
        self.PLANID = EDTController("str", DataType.String)
        self.NAME = EDTController("str", DataType.String)
        
        # Define relations
        self.relations = {
            "mensalities": self.new_Relation(PlanMensalities)
                              .on(self.PLANID, "PLANID")
                              .join_type_as('LEFT')
        }

# Configuração do AutoRouter
from flask import Flask
from SQLManager import CoreConfig, database_connection
from SQLManager.controller import AutoRouter

app = Flask(__name__)
db = database_connection()

# Registra rotas automaticamente
router = AutoRouter(db, app=app)

# Agora as rotas funcionam automaticamente:
# GET  /manager/SellerPlansTable       → Lista planos com mensalities
# GET  /manager/SellerPlansTable/1     → Busca plano específico com mensalities
# POST /manager/SellerPlansTable       → Cria novo plano
```

### Endpoints Gerados:

**1. Listagem (GET /manager/SellerPlansTable):**
```json
{
  "status": 200,
  "data": [
    {
      "RECID": 1,
      "PLANID": "PLN0003",
      "NAME": "Plano Premium",
      "relations": {
        "mensalities": [
          {"RECID": 10, "AMOUNT": 99.90},
          {"RECID": 11, "AMOUNT": 99.90}
        ]
      }
    }
  ],
  "meta": {"page": 1, "limit": 20, "count": 1}
}
```

**2. Detalhe (GET /manager/SellerPlansTable/1):**
```json
{
  "status": 200,
  "data": {
    "RECID": 1,
    "PLANID": "PLN0003",
    "NAME": "Plano Premium",
    "relations": {
      "mensalities": [
        {"RECID": 10, "PLANID": "PLN0003", "AMOUNT": 99.90}
      ]
    }
  }
}
```

**3. Com Filtros (GET /manager/SellerPlansTable?PLANID=PLN0003):**
As relations são incluídas automaticamente em todos os requests GET.

### Vantagens com AutoRouter:

- **Zero Código Extra:** Apenas defina as relations, o router faz o resto
- **Consistência:** Mesmo formato JSON em todos os endpoints
- **Performance:** Um único request retorna dados completos (evita N+1 queries)
- **Type Safety:** Validações de EDT aplicadas automaticamente
- **Documentação:** Postman collection gerada inclui relations

