"""
Script de teste para verificar se o AutoRouter está encontrando as tabelas.
Execute este script no seu projeto para debugar o problema.
"""

import importlib
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path se necessário
# Ajuste conforme sua estrutura
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("="*80)
print("TESTE DE DESCOBERTA DE TABELAS - AutoRouter")
print("="*80)

# Tenta importar diferentes estruturas
possible_modules = [
    "model.TablePack",
    "src.model.TablePack",
    "model.tables",
    "src.model.tables",
]

print("\n1. Tentando importar módulos TablePack...")
for mod_name in possible_modules:
    try:
        module = importlib.import_module(mod_name)
        print(f"   ✓ {mod_name} - ENCONTRADO")
        
        # Verifica se tem __all__
        if hasattr(module, '__all__'):
            print(f"     -> __all__ definido com {len(module.__all__)} itens:")
            for item in module.__all__[:5]:  # Mostra apenas os primeiros 5
                print(f"        - {item}")
            if len(module.__all__) > 5:
                print(f"        ... e mais {len(module.__all__) - 5} itens")
        else:
            print(f"     -> __all__ NÃO definido")
            # Mostra alguns itens do dir()
            items = [n for n in dir(module) if not n.startswith('_')][:5]
            print(f"     -> dir() retorna {len(items)} itens (primeiros 5):")
            for item in items:
                print(f"        - {item}")
        
        # Verifica se são classes
        print(f"     -> Verificando tipos...")
        classes_found = []
        items_to_check = module.__all__ if hasattr(module, '__all__') else [n for n in dir(module) if not n.startswith('_')]
        
        for name in items_to_check:
            try:
                attr = getattr(module, name)
                if isinstance(attr, type):
                    classes_found.append(name)
            except:
                pass
        
        print(f"     -> Classes encontradas: {len(classes_found)}")
        if classes_found:
            print(f"        Exemplos: {', '.join(classes_found[:3])}")
        
        print()
        break  # Encontrou, para de tentar
        
    except ImportError as e:
        print(f"   ✗ {mod_name} - Não encontrado ({str(e)})")

print("\n2. Verificando estrutura do projeto...")
print(f"   sys.path inclui:")
for p in sys.path[:3]:
    print(f"     - {p}")

print("\n" + "="*80)
print("DICA: Se nenhum módulo foi encontrado, verifique:")
print("  1. A estrutura de pastas do seu projeto")
print("  2. Se há __init__.py nos diretórios necessários")
print("  3. Se você está executando de dentro do ambiente virtual correto")
print("="*80)
