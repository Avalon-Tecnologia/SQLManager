''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

from typing import TYPE_CHECKING

from .. import *

class EDT_Manager:
    '''Gerenciamento de EDTs'''
    
    def _scan_existing_edts(_model, _ShowEDTs: bool = False):
        '''Escaneia EDTs existentes no diretório'''
        import re
        
        for file in _model.edts_path.glob("*.py"):
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
            
            _model.available_edts[class_name.upper()] = class_name
            _model.edt_file_to_class[file_name] = class_name
        
        print(f"Encontrados: {SystemController().custom_text(len(_model.available_edts), 'red', is_bold=True)} EDTs")

        if(_ShowEDTs):
            print("Lista de EDTs encontrados:")
            for edt in _model.available_edts.values():
                print(f" - {SystemController().custom_text(edt, 'green', is_bold=True)}")
                
    def _update_edts_init(_model):
        '''Atualiza __init__.py dos EDTs'''
        init_file = _model.edts_path / "__init__.py"
                
        lines = []
        for file_name, class_name in _model.edt_file_to_class.items():
            lines.append(f"from .{file_name} import {class_name}")

        lines.append("")
        lines.append("__all__ = [")

        for edt in _model.available_edts.values():
            lines.append(f"    \"{edt}\",")

        lines.append("]")                    
        content = "\n".join(lines)
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Pacote de EDTs atualizado: {init_file}")

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''