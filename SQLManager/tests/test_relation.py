''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
from . import *

CoreConfig.configure(load_from_env=False,                    
                     db_user="XX",
                     db_password="XX",
                     db_server="XX",
                     db_database="XX")

database = data()
database.connect()

class PlanMensalities(TableController):
   
    '''
    Tabela: PlanMensalities
    args:
        db_controller: Banco de dados ou transação
    '''
    def __init__(self, db):
        super().__init__(db=db, source_name="PlanMensalities")
   
        self.RECID = Recid()
        self.CREATEDATETIME = EDTController("datetime", DataType.DateTime)
        self.PLANID = EDTController("any", DataType.String) 
        self.AMOUNT = EDTController("float", DataType.Float)

class SellerPlansTable(TableController):
   
    '''
    Tabela: SellerPlansTable
    args:
        db_controller: Banco de dados ou transação
    '''
    def __init__(self, db):
        super().__init__(db=db, source_name="SellerPlansTable")
   
        self.RECID = Recid()
        self.CREATEDATETIME = EDTController("datetime", DataType.DateTime)
        self.PLANID = EDTController("any", DataType.String)  
        self.NAME = EDTController("any", DataType.String)
        self.DESCRIPTION = EDTController("any", DataType.String)
        self.ISDISABLE = EDTController("bool", DataType.Boolean)
        self.STARTDATE = EDTController("date", DataType.Date)
        self.ENDDATE = EDTController("date", DataType.Date)
        
        self.relations = {
            "mensalities": self.new_Relation(PlanMensalities)
                              .on(self.PLANID, "PLANID")  
                              .join_type_as('LEFT')
        }

# ===== TESTE 1: SELECT com Relations Automáticas =====
print("=" * 60)
print("TESTE 1: SELECT com Relations Automáticas")
print("=" * 60)

with database.transaction() as trs:
    seller_plans = SellerPlansTable(trs)    
    
    # SELECT com relation automática - Traz os dados relacionados automaticamente
    seller_plans.select().with_relations("mensalities").where(seller_plans.PLANID == "PLN0003").execute()
    
    print(f"\nPLANO (Main Table):")
    print(f"  Total de records: {len(seller_plans.records)}")
    if seller_plans.records:
        print(f"  Primeiro record: {seller_plans.records[0]}")
        print(f"  PLANID atual: {seller_plans.PLANID}")
        print(f"  NAME atual: {seller_plans.NAME}")
    
    print(f"\nMENSALIDADES (Relation):")
    mensalities_rel = seller_plans.relations["mensalities"]
    print(f"  Total de mensalities: {len(mensalities_rel.records)}")
    if mensalities_rel.records:
        print(f"  Primeiras 3 mensalities:")
        for i, rec in enumerate(mensalities_rel.records[:3]):
            print(f"    [{i}] {rec}")
        
        # Acessando através da instância da tabela relacionada
        print(f"\n  Através da instância da tabela:")
        print(f"    AMOUNT atual: {mensalities_rel.get_instance().AMOUNT}")

# ===== TESTE 2: SELECT sem Relations (modo tradicional) =====
print("\n" + "=" * 60)
print("TESTE 2: SELECT Tradicional (sem relations)")
print("=" * 60)

with database.transaction() as trs:
    seller_plans = SellerPlansTable(trs)
    
    # SELECT simples sem relations
    seller_plans.select().where(seller_plans.PLANID == "PLN0003").execute()
    
    print(f"\nPLANO:")
    print(f"  Total de records: {len(seller_plans.records)}")
    print(f"  PLANID: {seller_plans.PLANID}")
    print(f"  NAME: {seller_plans.NAME}")

# ===== TESTE 3: Multiple Relations (se houver) =====
print("\n" + "=" * 60)
print("TESTE 3: Iteração pelos records da relation")
print("=" * 60)

with database.transaction() as trs:
    seller_plans = SellerPlansTable(trs)    
    
    # Busca múltiplos planos
    seller_plans.select().with_relations("mensalities").limit(3).execute()
    
    print(f"\nTotal de planos encontrados: {len(seller_plans.records)}")
    
    # Acessa a relation
    mensalities = seller_plans.relations["mensalities"]
    
    print(f"\nTODAS as mensalidades dos planos (agregadas):")
    print(f"  Total: {len(mensalities.records)}")
    
    # Itera pelos records da relation
    for i, mens_record in enumerate(mensalities.records[:5]):  # Primeiros 5
        print(f"  [{i}] PLANID: {mens_record.get('PLANID')}, AMOUNT: {mens_record.get('AMOUNT')}")

print("\n" + "=" * 60)
print("Fim dos testes")
print("=" * 60)
''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''