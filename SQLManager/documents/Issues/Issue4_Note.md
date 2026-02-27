# Issues [#4-ViewController](https://github.com/nickzsd/SQLManager/issues/4) - SQLManager

## O que foi feito
Desenvolvido um novo arquivo `ViewController` onde possui uma funcionalidade semelhante a `TableController` porem com enfase em views no banco de dados.

## Utilização
Utilizar da mesma maneira que é feito com a tableController
Suas funcionalidade é:

**Declaração**
```Python
class PlansDataSet(ViewController):
    def __init__(self, db):
        super().__init__(db, "PlansDataSet")

        self.PLAN_RECID = Recid()
        self.AMOUNT     = EDTController("float", DataType.Float)
        self.STARTDATE  = EDTController("date", DataType.Date)
        self.ENDDATE    = EDTController("date", DataType.Date)
    pass
```

**Utilização**
```Python
with database.transaction() as trs:
    view = PlansDataSet(trs)
    view.select().execute()        

    for record in view.records:
        view.set_current(record)                

        print(view.PLAN_RECID)
        print(view.AMOUNT)
        print(view.STARTDATE)
        print(view.ENDDATE)
```

> Arquivo teste [test_view.py](SQLManager/tests/test_view.py)  
> AVISO: é um arquivo modelo de testes para criação das views

## Mudanças
### *Setup.py*
```Python
package_data={
    "SQLManager": [
        "_model/*.py",
        "EDTs/*.py",
        "enum/*.py",
        "tables/*.py",
        "views/*.py", <- Novo Package da Manager
    ]
}
```
### *_init_.py*
```Python
from .EDTController      import EDTController
from .BaseEnumController import BaseEnumController
from .TableController    import TableController
from .SystemController   import SystemController

''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''

from .ViewController    import ViewController <- Novo

__all__ = [
    'EDTController',
    'BaseEnumController',
    'TableController',
    'ViewController', <- Novo
    'SystemController'
]
''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''
```
### *_Model_Update.py*
```Python
init_files = [
    model_path / "EDTs" / "__init__.py",
    model_path / "enum" / "__init__.py",
    model_path / "tables" / "__init__.py",

    model_path / "views" / "__init__.py" <- novo
]
```
> Paths relativos a model

```Python
content = (
    "from . import EDTs   as EDTPack\n"
    "from . import enum   as EnumPack\n"
    "from . import views  as ViewPack\n" <- Novo
    "from . import tables as TablePack\n\n"
    "__all__ = [\n"
    "    \"EDTPack\",\n"
    "    \"EnumPack\",\n"
    "    \"ViewPack\",\n" <- Novo
    "    \"TablePack\",\n"
    "]\n"
)
```

> atualiza o init base da model do sistema

```Python
self.model_path  = project_root / "src" / "model"
self.edts_path   = self.model_path  / "EDTs"
self.enums_path  = self.model_path  / "enum"
self.tables_path = self.model_path  / "tables"
self.views_path  = self.model_path  / "views" <- Novo

self.edts_path.mkdir(parents=True, exist_ok=True)
self.enums_path.mkdir(parents=True, exist_ok=True)
self.tables_path.mkdir(parents=True, exist_ok=True)
self.views_path.mkdir(parents=True, exist_ok=True) <- Novo
        
self.available_edts   = {}
self.available_enums  = {}
self.available_tables = {}
self.available_views  = {} <- Novo
        
self.edt_file_to_class   = {}
self.enum_file_to_class  = {}
self.table_file_to_class = {}
self.view_file_to_class  = {} <- Novo
```

> atualiza a classe chave de geração de model

```Python
def _clear_init_files(self):
    '''Limpa arquivos __init__.py de EDTs, Enums, Tables e Views'''
    init_files = [
        self.edts_path / "__init__.py",
        self.enums_path / "__init__.py",
        self.tables_path / "__init__.py",
        self.views_path / "__init__.py" <- Novo
    ]
```

> limpeza de arquivo de cada modulo da model

```Python
#Arquivo completamente novo

utils.stepInfo("04.1", "Escaneando Views existentes")
View_Manager._scan_existing_views(self, _ShowViews=True)

utils.stepInfo("04.2", "Atualizando Views")
View_Manager._update_views(self)

utils.stepInfo("04.3", "Atualizando model de Views")
View_Manager._update_views_init(self)
```

> Passos de criação, analise e atualização das views do sistema.


```Python
# Classe que trata completamente a model
class View_Manager:
```

**Principais métodos:**
- `_scan_existing_views()`: Analisa as views ja existentes no diretorio.
- `_update_views()`: Atualiza o modulo de views com base nas views faltantes no sistema.
- `_update_views_init()`: atualiza o init do modulo com todas as view criadas e existentes.
- `_update_single_view`: Atualiza/Cria Enums e EDTs da view caso ele não exista.
- `_update_existing_view`: Atualiza a view com Enums e EDTs.
- `_generate_View_class`: Gera uma view na formatação do Python.
> AVISO: Todas as atualizações preservão completamento os metodos ou customizações, eles somente atualização ENUMs ou EDTs faltantes.
