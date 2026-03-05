''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

from typing import TYPE_CHECKING

from .. import *

class View_Manager:
    '''Gerenciamento de Views'''
    
    def _scan_existing_views(_model, _ShowViews: bool = False):
        '''Escaneia Views existentes no diretório'''
        import re
        
        for file in _model.views_path.glob("*.py"):
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
            
            _model.available_views[class_name] = file
            _model.view_file_to_class[file_name] = class_name
        
        print(f"Encontrados {SystemController().custom_text(len(_model.available_views), 'red', is_bold=True)} Views")

        if(_ShowViews):
            print("Lista de Views encontrados:")
            for view in _model.available_views.keys():
                print(f" - {view}")

    def _update_views(_model):
        '''Atualiza Views baseadas no banco de dados'''        
        query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.VIEWS
            ORDER BY TABLE_NAME
        """
        
        views    = _model.db.doQuery(query)
        db_views = [row[0] for row in views]
        
        print(f"Encontradas {SystemController().custom_text(len(db_views), 'red', is_bold=True)} Views no banco de dados")                        
        
        skipped_views = []
        for view_name in db_views:
            error_info = View_Manager._update_single_view(_model, view_name)
            if error_info:
                skipped_views.append(error_info)
                
        db_views_lower = set(v.lower() for v in db_views)
                
        views_to_remove = [
            (view_name, file_path)
            for view_name, file_path in _model.available_views.items()
            if view_name.lower() not in db_views_lower
        ]

        for view_name, file_path in views_to_remove:
            print(f"\nView '{SystemController().custom_text(view_name, 'red')}' removida da aplicação pois não existe no banco de dados!")
            file_path.unlink()
            if view_name in _model.available_views:
                del _model.available_views[view_name]
            file_stem = file_path.stem
            if file_stem in _model.view_file_to_class:
                del _model.view_file_to_class[file_stem]
        
        if skipped_views:
            print(f"\n{SystemController().custom_text('VIEWS NÃO PROCESSADAS', 'yellow', is_bold=True)}")
            print("="*60)
            for error_info in skipped_views:
                print(f"{SystemController().custom_text('View:', 'cyan')} {error_info['view']}")
                print(f"{SystemController().custom_text('Motivo:', 'red')} {error_info['reason']}")
                print("-"*60)
        
        View_Manager._scan_existing_views(_model, _ShowViews=True)

    def _update_views_init(_model):
        '''Atualiza __init__.py de views'''
        init_file = _model.views_path / "__init__.py"
                
        lines = []
        for file_name, class_name in _model.view_file_to_class.items():
            lines.append(f"from .{file_name} import {class_name}")

        lines.append("")
        lines.append("__all__ = [")

        for view in _model.available_views.keys():
            lines.append(f"    \"{view}\",")

        lines.append("]")                    
        content = "\n".join(lines)
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Pacote de Views atualizado: {init_file}")

    def _update_single_view(_model, view_name: str):
        '''
        Atualiza/Cria view específica
        Returns: Dict com erro ou None se sucesso
        '''        
        query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """
        
        columns = _model.db.doQuery(query, (view_name,))
        
        if not columns:
            return {'view': view_name, 'reason': 'View sem colunas'}
        
        ''' View não tem RECID Obrigatorio
        recid_column = None
        for col in columns:
            if col[0].upper() == 'RECID':
                recid_column = col
                break
        
        if not recid_column:
            return {'View': view_name, 'reason': 'Campo RECID obrigatório não encontrado'}
    
            
        recid_type = recid_column[1].lower()
        if recid_type != 'bigint':
            return {'View': view_name, 'reason': f'Campo RECID deve ser BIGINT (encontrado: {recid_type.upper()})'}
        '''        
        
        view_file = _model.views_path / f"{view_name}.py"
        
        try:
            if view_file.exists():
                view_code = View_Manager._update_existing_view(_model, view_name, columns, view_file)
            else:
                view_code = View_Manager._generate_View_class(_model, view_name, columns)
                    
            with open(view_file, 'w', encoding='utf-8') as f:
                f.write(view_code)
            
            print(f"Atualizada: {SystemController().custom_text(view_name, 'green', is_bold=True)}")
            return None
        except Exception as e:
            return {'view': view_name, 'reason': f'Erro ao gerar código: {str(e)}'}
    
    def _update_existing_view(_model, view_name: str, columns, view_file: Path) -> str:
        '''Atualiza view existente preservando métodos customizados'''
        import re
        
        with open(view_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        existing_fields = {}
        field_pattern   = r'self\.(\w+)\s*=\s*(.+)'
        for match in re.finditer(field_pattern, existing_content):
            field_name = match.group(1)
            field_value = match.group(2).strip()
            existing_fields[field_name] = field_value
        
        new_fields     = {}
        db_field_names = set()
        updated_fields = []
        
        for col in columns:
            col_name   = col[0].upper()
            sql_type   = col[1].lower()
            max_length = col[3]
            db_field_names.add(col_name)
            
            new_field_type = View_Manager._detect_field_type(_model, col_name, sql_type, max_length)
            
            if col_name in existing_fields:
                existing_def = existing_fields[col_name]
                
                # Verifica se tem EDT/Enum customizado específico
                has_custom_edt  = 'EDTPack.' in existing_def and existing_def != new_field_type
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
            print(f"  - View {SystemController().custom_text(view_name, 'cyan')}: {SystemController().custom_text('Campos adicionados', 'yellow')} - {', '.join(sorted(new_field_names))}")
        
        if updated_fields:
            print(f"  - View {SystemController().custom_text(view_name, 'cyan')}: {SystemController().custom_text('Campos atualizados com EDT/Enum', 'green')} - {', '.join(sorted(updated_fields))}")
        
        removed_field_names = existing_field_names - db_field_names
        if removed_field_names:
            print(f"  - View {SystemController().custom_text(view_name, 'cyan')}: {SystemController().custom_text('Campos removidos do banco', 'red')} - {', '.join(sorted(removed_field_names))}")
        
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
        lines.append("from SQLManager import ViewController, EDTController")
        lines.append("from model import EDTPack, EnumPack")
        lines.append("")
        lines.append(f"class {view_name}(ViewController):")
        lines.append("    ")
        lines.append("    '''")
        lines.append(f"    View: {view_name}")
        lines.append("    args:")
        lines.append("        db_controller: Banco de dados ou transação")
        lines.append("    '''")
        lines.append("    def __init__(self, db):")
        lines.append(f"        super().__init__(db=db, source_name=\"{view_name}\")")
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
    
    def _generate_View_class(_model, view_name: str, columns) -> str:
        '''Gera código Python para classe de view'''
        lines = []
                
        lines.append("from SQLManager import ViewController, EDTController")
        lines.append("from model import EDTPack, EnumPack")        
        lines.append("")
                
        lines.append(f"class {view_name}(ViewController):")
        lines.append("    ")
        lines.append("    '''")
        lines.append(f"    View: {view_name}")
        lines.append("    args:")
        lines.append("        db_controller: Banco de dados ou transação")
        lines.append("    '''")
        lines.append("    def __init__(self, db):")
        lines.append(f"        super().__init__(db=db, source_name=\"{view_name}\")")
        lines.append("    ")
                
        for col in columns:
            col_name   = col[0].upper()
            sql_type   = col[1].lower()
            max_length = col[3]
                        
            field_def = View_Manager._detect_field_type(_model, col_name, sql_type, max_length)
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