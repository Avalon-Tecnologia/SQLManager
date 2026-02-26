''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
from . import *

CoreConfig.configure(load_from_env=False,                    
                     db_user="Matheus_Salvagno",
                     db_password="AvT@Matheus",
                     db_server="100.108.119.125,15433",
                     db_database="Seller_Center")

database = data()
database.connect()

class PlansDataSet(ViewController):
    def __init__(self, db):
        super().__init__(db, "PlansDataSet")

        self.PLAN_RECID = Recid()
        self.AMOUNT     = EDTController("float", DataType.Float)
        self.STARTDATE  = EDTController("date", DataType.Date)
        self.ENDDATE    = EDTController("date", DataType.Date)
    pass

with database.transaction() as trs:
    view = PlansDataSet(trs)
    view.select().execute()        

    for record in view.records:
        view.set_current(record)                

        print(view.PLAN_RECID)
        print(view.AMOUNT)
        print(view.STARTDATE)
        print(view.ENDDATE)

print("Fim do teste")
''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''