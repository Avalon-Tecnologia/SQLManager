''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

from typing import TYPE_CHECKING

from .. import *

class Table_Manager:
    '''Gerenciamento de Tables'''
    
    def _scan_existing_tables(_model, _ShowTables: bool = False):
        '''Escaneia Tables existentes no diretório'''
        import re
        
        for file in _model.tables_path.glob("*.py"):
            if file.name.startswith("_") or file.name == "__init__.py":
                continue
                        
            file_name = file.stem
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()                
                match = re.search(r'^class\s+(\w+)\s*\(', content, re.MULTILINE)
                if match:
                    class_name = match.group(1)
                else:                    
                    class_name = file_name
            
            _model.available_tables[class_name] = file
            _model.table_file_to_class[file_name] = class_name
        
        print(f"Encontrados {SystemController().custom_text(len(_model.available_tables), 'red', is_bold=True)} Tables")

        if(_ShowTables):
            print("Lista de Tables encontrados:")
            for table in _model.available_tables.keys():
                print(f" - {table}")

    def _update_tables(_model):
        '''Atualiza Tables baseadas no banco de dados'''        
        query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        
        tables = _model.db.doQuery(query)
        db_tables = [row[0] for row in tables]
        
        print(f"Encontradas {SystemController().custom_text(len(db_tables), 'red', is_bold=True)} tabelas no banco de dados")                        
        
        skipped_tables = []
        for table_name in db_tables:
            error_info = Table_Manager._update_single_table(_model, table_name)
            if error_info:
                skipped_tables.append(error_info)
                
        db_tables_lower = set(t.lower() for t in db_tables)
                
        tables_to_remove = [
            (table_name, file_path)
            for table_name, file_path in _model.available_tables.items()
            if table_name.lower() not in db_tables_lower
        ]

        for table_name, file_path in tables_to_remove:
            print(f"\nTabela '{SystemController().custom_text(table_name, 'red')}' removida da aplicação pois não existe no banco de dados!")
            file_path.unlink()
            if table_name in _model.available_tables:
                del _model.available_tables[table_name]
            file_stem = file_path.stem
            if file_stem in _model.table_file_to_class:
                del _model.table_file_to_class[file_stem]
        
        if skipped_tables:
            print(f"\n{SystemController().custom_text('TABELAS NÃO PROCESSADAS', 'yellow', is_bold=True)}")
            print("="*60)
            for error_info in skipped_tables:
                print(f"{SystemController().custom_text('Tabela:', 'cyan')} {error_info['table']}")
                print(f"{SystemController().custom_text('Motivo:', 'red')} {error_info['reason']}")
                print("-"*60)
        
        Table_Manager._scan_existing_tables(_model, _ShowTables=True)

    def _update_tables_init(_model):
        '''Atualiza __init__.py de tables'''
        init_file = _model.tables_path / "__init__.py"
                
        lines = []
        for file_name, class_name in _model.table_file_to_class.items():
            lines.append(f"from .{file_name} import {class_name}")

        lines.append("")
        lines.append("__all__ = [")

        for table in _model.available_tables.keys():
            lines.append(f"    \"{table}\",")

        lines.append("]")                    
        content = "\n".join(lines)
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Pacote de Tables atualizado: {init_file}")

    def _update_single_table(_model, table_name: str):
        '''
        Atualiza/Cria tabela específica
        Returns: Dict com erro ou None se sucesso
        '''        
        query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        
        columns = _model.db.doQuery(query, (table_name,))
        
        if not columns:
            return {'table': table_name, 'reason': 'Tabela sem colunas'}
        
        recid_column = None
        for col in columns:
            if col[0].upper() == 'RECID':
                recid_column = col
                break
        
        if not recid_column:
            return {'table': table_name, 'reason': 'Campo RECID obrigatório não encontrado'}
                
        recid_type = recid_column[1].lower()
        if recid_type != 'bigint':
            return {'table': table_name, 'reason': f'Campo RECID deve ser BIGINT (encontrado: {recid_type.upper()})'}
        
        table_file = _model.tables_path / f"{table_name}.py"
        
        try:
            if table_file.exists():
                table_code = Table_Manager._update_existing_table(_model, table_name, columns, table_file)
            else:
                table_code = Table_Manager._generate_table_class(_model, table_name, columns)
                    
            with open(table_file, 'w', encoding='utf-8') as f:
                f.write(table_code)
            
            print(f"Atualizada: {SystemController().custom_text(table_name, 'green', is_bold=True)}")
            return None
        except Exception as e:
            return {'table': table_name, 'reason': f'Erro ao gerar código: {str(e)}'}
    
    def _update_existing_table(_model, table_name: str, columns, table_file: Path) -> str:
        '''Atualiza tabela existente preservando métodos customizados'''
        import re
        
        with open(table_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        existing_fields = {}
        field_pattern = r'self\.(\w+)\s*=\s*(.+)'
        for match in re.finditer(field_pattern, existing_content):
            field_name = match.group(1)
            field_value = match.group(2).strip()
            existing_fields[field_name] = field_value
        
        new_fields = {}
        db_field_names = set()
        updated_fields = []
        
        for col in columns:
            col_name = col[0].upper()
            sql_type = col[1].lower()
            max_length = col[3]
            db_field_names.add(col_name)
            
            new_field_type = Table_Manager._detect_field_type(_model, col_name, sql_type, max_length)
            
            if col_name in existing_fields:
                existing_def = existing_fields[col_name]
                
                # Verifica se tem EDT/Enum customizado específico
                has_custom_edt = 'EDTPack.' in existing_def and existing_def != new_field_type
                has_custom_enum = 'EnumPack.' in existing_def and 'Enum_cls' not in existing_def and existing_def != new_field_type
                
                if has_custom_edt or has_custom_enum:
                    # Mantém customização específica
                    new_fields[col_name] = existing_def
                else:
                    # Atualiza para novo EDT/Enum se disponível ou usa genérico
                    if existing_def != new_field_type:
                        updated_fields.append(col_name)
                    new_fields[col_name] = new_field_type
            else:
                # Campo novo
                new_fields[col_name] = new_field_type
        
        existing_field_names = set(existing_fields.keys())
        
        new_field_names = db_field_names - existing_field_names
        if new_field_names:
            print(f"  - Tabela {SystemController().custom_text(table_name, 'cyan')}: {SystemController().custom_text('Campos adicionados', 'yellow')} - {', '.join(sorted(new_field_names))}")
        
        if updated_fields:
            print(f"  - Tabela {SystemController().custom_text(table_name, 'cyan')}: {SystemController().custom_text('Campos atualizados com EDT/Enum', 'green')} - {', '.join(sorted(updated_fields))}")
        
        removed_field_names = existing_field_names - db_field_names
        if removed_field_names:
            print(f"  - Tabela {SystemController().custom_text(table_name, 'cyan')}: {SystemController().custom_text('Campos removidos do banco', 'red')} - {', '.join(sorted(removed_field_names))}")
        
        init_end_pattern = r'(self\.\w+\s*=\s*.+?)(\n\n|\n    def |\nclass |\Z)'
        matches = list(re.finditer(init_end_pattern, existing_content, re.DOTALL))
        
        custom_methods = ""
        if matches:
            last_field_end = matches[-1].end(1)
            rest_of_file = existing_content[last_field_end:]
            custom_pattern = r'(\n    def (?!__init__)\w+.+?)(?=\nclass |\Z)'
            custom_match = re.search(custom_pattern, rest_of_file, re.DOTALL)
            if custom_match:
                custom_methods = custom_match.group(1)
        
        lines = []
        lines.append("from SQLManager import TableController, EDTController")
        lines.append("from model import EDTPack, EnumPack")
        lines.append("")
        lines.append(f"class {table_name}(TableController):")
        lines.append("    ")
        lines.append("    '''")
        lines.append(f"    Tabela: {table_name}")
        lines.append("    args:")
        lines.append("        db_controller: Banco de dados ou transação")
        lines.append("    '''")
        lines.append("    def __init__(self, db):")
        lines.append(f"        super().__init__(db=db, source_name=\"{table_name}\")")
        lines.append("    ")
        
        for col in columns:
            col_name = col[0].upper()
            if col_name in new_fields:
                lines.append(f"        self.{col_name} = {new_fields[col_name]}")
        
        lines.append("")
        
        if custom_methods:
            lines.append(custom_methods.rstrip())
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_table_class(_model, table_name: str, columns) -> str:
        '''Gera código Python para classe de tabela'''
        lines = []
                
        lines.append("from SQLManager import TableController, EDTController")
        lines.append("from model import EDTPack, EnumPack")        
        lines.append("")
                
        lines.append(f"class {table_name}(TableController):")
        lines.append("    ")
        lines.append("    '''")
        lines.append(f"    Tabela: {table_name}")
        lines.append("    args:")
        lines.append("        db_controller: Banco de dados ou transação")
        lines.append("    '''")
        lines.append("    def __init__(self, db):")
        lines.append(f"        super().__init__(db=db, source_name=\"{table_name}\")")
        lines.append("    ")
                
        for col in columns:
            col_name = col[0].upper()
            sql_type = col[1].lower()
            max_length = col[3]
                        
            field_def = Table_Manager._detect_field_type(_model, col_name, sql_type, max_length)
            lines.append(f"        self.{col_name} = {field_def}")
        
        lines.append("")
        
        return "\n".join(lines)
        
    def _detect_field_type(_model, field_name: str, sql_type: str, max_length) -> str:
        '''Detecta tipo de campo apropriado (EDT, Enum ou padrão)'''
                
        if field_name in _model.available_edts:
            return f"EDTPack.{_model.available_edts[field_name]}()"
                    
        if field_name in _model.available_enums:
            return f"EnumPack.{_model.available_enums[field_name]}()"
                
        python_type, datatype = _model.sql_type_mapping.get(sql_type, ('str', 'DataType.String'))
                
        datatype_name = datatype.split('.')[-1]

        if sql_type in ('varchar', 'nvarchar', 'char', 'nchar') and max_length:
            return f"EDTController('any', EnumPack.DataType.{datatype_name}, None, {max_length})"
    
        return f"EDTController('any', EnumPack.DataType.{datatype_name})"

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''