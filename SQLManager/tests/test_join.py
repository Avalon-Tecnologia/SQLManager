''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
from . import *

CoreConfig.configure(load_from_env=False,                    
                     db_user="XX",
                     db_password="XX",
                     db_server="XX",
                     db_database="XX")

database = data()
database.connect()

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
        self.PLANID = EDTController("int", DataType.Number)
        self.NAME = EDTController("str", DataType.String)
        self.DESCRIPTION = EDTController("str", DataType.String)
        self.ISDISABLE = EDTController("bool", DataType.Boolean)
        self.STARTDATE = EDTController("date", DataType.Date)
        self.ENDDATE = EDTController("date", DataType.Date)

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
        self.PLANID = EDTController("int", DataType.Number)
        self.AMOUNT = EDTController("float", DataType.Float)

with database.transaction() as trs:
    Table_SellerPlans     = SellerPlansTable(trs)
    Table_PlanMensalities = PlanMensalities(trs)
    Table_SellerPlans.select().join(Table_PlanMensalities).on((Table_SellerPlans.PLANID == Table_PlanMensalities.PLANID)).execute()        

    print(Table_SellerPlans.records)
    print(Table_PlanMensalities.records)

print("Fim do teste")
''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''