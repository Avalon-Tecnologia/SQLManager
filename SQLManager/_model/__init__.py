''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''
from SQLManager import CoreConfig, database_connection, SystemController

# //=== DOTENV - CHECK ===//

try:
    import dotenv
except ImportError:
    dotenv = None

import os
import sys

from typing  import TYPE_CHECKING
from pathlib import Path

# //=== ARGSPARSER ===//
import argparse
parser = argparse.ArgumentParser(description="SQLManager - Gerenciador de Modelos e Conexões SQL")
parser.add_argument("--server", help="Servidor do banco de dados", type=str)
parser.add_argument("--database", help="Banco de dados", type=str)
parser.add_argument("--user", help="Usuário do banco de dados", type=str)
parser.add_argument("--password", help="Senha do banco de dados", type=str)
parser.add_argument("--driver", help="Driver ODBC para SQL Server (ex: 'ODBC Driver 17 for SQL Server')", type=str)
args = parser.parse_args()

# //=== DIR PATHS ===//

ROOT_DIR = Path(__file__).parent.parent.parent.parent

sys.dont_write_bytecode = True
src_dir = ROOT_DIR / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(ROOT_DIR))

# //=== DOTENV - CHECK ===//

if(dotenv is not None):    
    dotenv.load_dotenv()
else: 
    print(f"{SystemController.custom_text('Erro', 'red')}: python-dotenv não encontrado. Variáveis de ambiente do .env não serão carregadas.")
    print(f"{SystemController.custom_text('Aviso', 'yellow')}: Caso não possua env seguir a instruções do README para configuração manual.")

# //=== UTILS ===//

from ._utils import utils as utils_class

utils = utils_class()

if utils is not None:
    utils._clear_init_files_pre_import()

# //=== CONFIG ===//    
if(dotenv is not None):
    CoreConfig.configure(
        db_server   = os.getenv('DB_SERVER'),
        db_database = os.getenv('DB_DATABASE'),
        db_user     = os.getenv('DB_USER'),
        db_password = os.getenv('DB_PASSWORD'),
        db_driver   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    )
else:
    CoreConfig.configure(
        db_server   = args.server,
        db_database = args.database,
        db_user     = args.user,
        db_password = args.password,
        db_driver   = args.driver or 'ODBC Driver 17 for SQL Server'
    )

if(CoreConfig.is_configured()):
    print(f"{SystemController.custom_text('Configuração carregada com sucesso', 'green')}")
else:
    print(f"{SystemController.custom_text('Erro ao carregar configuração', 'red')}: Verifique as variáveis de ambiente ou os argumentos passados.")
    print(f"{SystemController.custom_text('Aviso', 'yellow')}: Sem configuração válida, conexões com o banco de dados não funcionarão.")


# //=== PATHs ===//
model_path = ROOT_DIR / "src" / "model"

init_files = [
    model_path / "EDTs"   / "__init__.py",
    model_path / "enum"   / "__init__.py",
    model_path / "tables" / "__init__.py",
    model_path / "views"  / "__init__.py"            
]

# //=== IMPORTS ===//
from .generators import EDTs, enums, tables
from .managers   import View_Manager, Table_Manager, Enum_Manager, EDT_Manager


__all__ = ["utils","CoreConfig","database_connection",
           "SystemController","sys",'os','dotenv','Path',
           'ROOT_DIR','src_dir', 'init_files', 'model_path',
           "EDTs", "enums", "tables",
           "View_Manager", "Table_Manager", "Enum_Manager", "EDT_Manager"]

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''