''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

from typing import TYPE_CHECKING

from .. import *

class Enum_Manager:
    '''Gerenciamento de Enums'''

    def _scan_existing_enums(_model, _ShowEnums: bool = False):
        '''Escaneia Enums existentes no diretório'''
        import re
        
        for file in _model.enums_path.glob("*.py"):
            if file.name.startswith("_") or file.name == "__init__.py":
                continue
                        
            file_name = file.stem
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()                                
                match = re.search(r'^class\s+(\w+)\s*\(\s*BaseEnumController\.Enum\s*\)', content, re.MULTILINE)
                if match:
                    class_name = match.group(1)
                else:                    
                    class_name = file_name
            
            _model.available_enums[class_name.upper()] = class_name
            _model.enum_file_to_class[file_name] = class_name
        
        print(f"Encontrados {SystemController().custom_text(len(_model.available_enums), 'red', is_bold=True)} Enums")

        if(_ShowEnums):
            print("Lista de Enums encontrados:")
            for enum in _model.available_enums.values():
                print(f" - {SystemController().custom_text(enum, 'green', is_bold=True)}")

    def _update_enums_init(_model):
        '''Atualiza __init__.py dos Enums'''
        init_file = _model.enums_path / "__init__.py"
                
        lines = []
        for file_name, class_name in _model.enum_file_to_class.items():
            lines.append(f"from .{file_name} import {class_name}")

        lines.append("")
        lines.append("__all__ = [")

        for enum in _model.available_enums.values():
            lines.append(f"    \"{enum}\",")

        lines.append("]")                    
        content = "\n".join(lines)
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Pacote de Enums atualizado: {init_file}")

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''