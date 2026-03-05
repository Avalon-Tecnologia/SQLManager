''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''

'''
Atualização automática de modelos (EDTs, Enums, Tables e Views) baseada na estrutura do banco de dados SQL Server.
Lê banco de dados e sincroniza com aplicação, gerando __init__.py automaticamente
'''

from . import *

class ModelUpdater:
    '''Atualização automática de modelos'''

    @staticmethod
    def _get_values(obj):
        '''Retorna valores de dict ou lista de forma compatível'''
        if isinstance(obj, dict):
            return obj.values()
        elif isinstance(obj, list):
            return obj
        else:
            return obj

    def ensurer(self, ref_Path: Path, content: str):
        '''Garante que arquivo exista com conteúdo específico'''
        if not ref_Path.exists():
            with open(ref_Path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Criado: {SystemController().custom_text(ref_Path.name, 'green')}")
        else:
            print(f"Existente: {SystemController().custom_text(ref_Path.name, 'yellow')}")


    def _clear_init_files(self):
        '''Limpa arquivos __init__.py de EDTs, Enums, Tables e Views'''
        init_files = [
            self.edts_path   / "__init__.py",
            self.enums_path  / "__init__.py",
            self.tables_path / "__init__.py",
            self.views_path  / "__init__.py"
        ]
        
        for init_file in init_files:
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write("# Auto-generated file - será atualizado automaticamente\n\n__all__ = []\n")
        
        print(SystemController().custom_text("Arquivos __init__.py limpos", "red", is_bold=True))

    def _generate_model_init(self):
        '''Gera __init__.py da pasta src/model/'''
        model_init_file = self.model_path / "__init__.py"
        content = (
            "from . import EDTs   as EDTPack\n"
            "from . import enum   as EnumPack\n"
            "from . import views  as ViewPack\n"
            "from . import tables as TablePack\n\n"
            "__all__ = [\n"
            "    \"EDTPack\",\n"
            "    \"EnumPack\",\n"
            "    \"ViewPack\",\n"
            "    \"TablePack\",\n"
            "]\n"
        )

        with open(model_init_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def __init__(self):
        self.db = database_connection()
        self.db.connect()
        
        project_root = Path.cwd()
        self.model_path  = project_root / "src" / "model"
        self.edts_path   = self.model_path  / "EDTs"
        self.enums_path  = self.model_path  / "enum"
        self.tables_path = self.model_path  / "tables"
        self.views_path  = self.model_path  / "views"

        self.edts_path.mkdir(parents=True, exist_ok=True)
        self.enums_path.mkdir(parents=True, exist_ok=True)
        self.tables_path.mkdir(parents=True, exist_ok=True)
        self.views_path.mkdir(parents=True, exist_ok=True)
                
        self.available_edts   = {}
        self.available_enums  = {}
        self.available_tables = {}
        self.available_views  = {}
                
        self.edt_file_to_class   = {}
        self.enum_file_to_class  = {}
        self.table_file_to_class = {}
        self.view_file_to_class  = {}
                
        self.sql_type_mapping = {
            'int':          ('int', 'DataType.Number'),
            'bigint':       ('int', 'DataType.Number'),
            'smallint':     ('int', 'DataType.Number'),
            'tinyint':      ('int', 'DataType.Number'),
            'bit':          ('bool', 'DataType.Boolean'),
            'decimal':      ('float', 'DataType.Float'),
            'numeric':      ('float', 'DataType.Float'),
            'money':        ('float', 'DataType.Float'),
            'float':        ('float', 'DataType.Float'),
            'real':         ('float', 'DataType.Float'),
            'varchar':      ('str', 'DataType.String'),
            'nvarchar':     ('str', 'DataType.String'),
            'char':         ('str', 'DataType.String'),
            'nchar':        ('str', 'DataType.String'),
            'text':         ('str', 'DataType.String'),
            'ntext':        ('str', 'DataType.String'),
            'datetime':     ('str', 'DataType.String'),
            'datetime2':    ('str', 'DataType.String'),
            'date':         ('str', 'DataType.String'),
            'time':         ('str', 'DataType.String'),
        }
    
    def __del__(self):
        '''Fecha conexão ao destruir objeto'''
        if hasattr(self, 'db'):
            self.db.disconnect()    
    
    def run(self):
        '''Executa atualização completa'''
        print("="*40)
        print("MODEL UPDATE")
        print("="*40)

        existing_tables = list(self.tables_path.glob("*.py"))
        existing_tables = [f for f in existing_tables if not f.name.startswith("_")]
        
        if existing_tables:
            print(f"\n{SystemController().custom_text('ATENÇÃO', 'red', is_bold=True)}")
            print(f"Tabelas não existentes no banco serão {SystemController().custom_text('REMOVIDAS', 'red', is_bold=True)}.")
            print(f"Faça {SystemController().custom_text('BACKUP', 'yellow', is_bold=True)} de src/model/tables antes de continuar.")
            print(f"\nContinuar? ({SystemController().custom_text('y', 'green')}/{SystemController().custom_text('n', 'red')})")

            resposta = input().strip().lower()

            if resposta != "y":
                print("Cancelado.")
                return

        try:            
            utils.stepInfo("00", "Limpando arquivos __init__.py")
            self._clear_init_files()

            utils.stepInfo("00.0", "Gerando __init__.py da pasta src/model/")
            self._generate_model_init()

            utils.stepInfo("00.1", "Garantindo Enums obrigatórios")
            for enum in self._get_values(enums):
                self.ensurer(self.enums_path, enum)

            utils.stepInfo("00.2", "Garantindo EDTs obrigatórios")
            for edt in self._get_values(EDTs):
                self.ensurer(self.edts_path, edt)

            utils.stepInfo("00.3", "Garantindo Tables obrigatórios")
            for table in self._get_values(tables):
                self.ensurer(self.tables_path, table)

            utils.stepInfo("01.1", "Escaneando EDTs existentes")
            EDT_Manager._scan_existing_edts(self, _ShowEDTs=True)

            utils.stepInfo("01.2", "Atualizando Model de EDTs")
            EDT_Manager._update_edts_init(self)

            utils.stepInfo("02.1", "Escaneando Enums existentes")
            Enum_Manager._scan_existing_enums(self, _ShowEnums=True)

            utils.stepInfo("02.2", "Atualizando Model de Enums")
            Enum_Manager._update_enums_init(self)

            utils.stepInfo("03.1", "Escaneando Tables existentes")
            Table_Manager._scan_existing_tables(self, _ShowTables=True)

            utils.stepInfo("03.2", "Atualizando Tables")
            Table_Manager._update_tables(self)

            utils.stepInfo("03.3", "Atualizando model de Tables")
            Table_Manager._scan_existing_tables(self, _ShowTables=True)
            Table_Manager._update_tables_init(self)

            utils.stepInfo("04.1", "Escaneando Views existentes")
            View_Manager._scan_existing_views(self, _ShowViews=True)

            utils.stepInfo("04.2", "Atualizando Views")
            View_Manager._update_views(self)

            utils.stepInfo("04.3", "Atualizando model de Views")
            View_Manager._update_views_init(self)

            print("\n" + "="*40)
            print("ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*40)

        except Exception as e:
            print(f"\n[ERRO] Falha na atualização: {str(e)}")
            raise
   
if __name__ == "__main__":
    updater = ModelUpdater().run()    

''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''