''' [BEGINs CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

import importlib


class utils:
    '''Funções utilitárias'''
    
    @staticmethod
    def _clear_init_files_pre_import():
        '''Limpa arquivos __init__.py antes de importar'''        
        pkg = importlib.import_module(__package__)
        init_files = getattr(pkg, 'init_files', [])

        for init_file in init_files:
            if init_file.exists():
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Auto-generated file - será atualizado automaticamente\n\n__all__ = []\n")


    @staticmethod
    def stepInfo(_step: str, _desc: str):        
        pkg = importlib.import_module(__package__)
        SystemController = getattr(pkg, 'SystemController', None)
        if SystemController is None:
            print(f"\n[{_step}] {_desc}...")
            return

        print(f"\n[{SystemController().custom_text(_step, 'cyan', is_bold=True)}] {_desc}...")

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''