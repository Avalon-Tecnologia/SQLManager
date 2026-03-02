#[BEGIN CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {02/03/2026}
from TableController import TableController

class NumberSequenceControler:

    def __init__(self, db):
        self.Header = TableController(db, "NumberSequenceTable")
        self.Lines  = TableController(db, "NumberSequenceLines")
        self.limit  = 20


    def getNextNum(self, reference:int ):
        """
            Função para buscar o proximo numero da sequencia

            :param reference: O RECID para fazer a busca do próximo numero da sequencia
            :type  reference: int
        """
        if reference == 0:
            return {"message": "Reference cannot be zero"}
        
        self.Header.select().where(self.Header.RECID == reference).join(self.Lines).on(self.Header.RECID == self.Lines.REFRECID).order_by(self.Lines.LINENUM).execute()
        if self.Header.rowcount() == 0 or self.Lines.rowcount() == 0:
            return {"message": "Sequence not found"}
        
        pad = len(str(self.HEADER.MAXNUM))

        return self.formatSequence(self.Lines.records, self.Header.CURNUM.value, pad)
    
    def confirmUse(self, reference:int):
        """
            Função para confimar o uso da sequencia

            :param reference: O RECID para confirmar o uso da sequencia
            :type  reference: int
        """

        if reference == 0:
            return {"message": "Reference cannot be zero"}
        
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines).on(self.Header.RECID == self.Lines.REFRECID).order_by(self.Lines.LINENUM).execute()
            if self.Header.rowcount() == 0 and self.Lines.rowcount() == 0:
                return {"message": "Sequence not found"}
            
            nextNum = self.Header.NEXTNUM.value
            self.Header.SelectForUpdate(True)

            self.Header.PREVNUM = self.Header.CURNUM.value
            self.Header.CURNUM = nextNum
            self.Header.NEXTNUM = nextNum + 1

            self.Header.update()

            return {"status": True, "message": "Sequence use confirmed"}
        except Exception as e:
            print("error: ", e)
            return {"status": False, "message": f"Unable to use due to: {e}"}

    def formatSequence(self, parts=None, number=1, padding=4):
        """
            Função para formatar a sequencia numerica

            :param parts: Dicionario com as partes em ordem da sequencia numerica
            :type parts: dict
        """
        if parts == None:
            if not self.Lines.records:
                return {"message": "Unable to find a suitable sequence to formar"}
            print("formating stored sequence")    
        
        parts = self.Lines.records
        ret = [len(parts)]
        for each in parts:
            if each.PARTTYPE.value == int: #TODO: colocar o ENUM pra usar de alfaNum para poder arrumar o padding
                ret[each.LINENUM.value] = str(number).rjust(padding, "0")
            else:
                ret[each.LINENUM.value] = each.SEQPART.value
        
        return str.join(ret)

    def createNumberSequence(self, header: dict, lines: list):
        """
            Função para criar uma nova sequencia numerica

            :param header: Dicionario com todos os valores que serão inseridos no header
            :type header: dict
            :param lines: Lista com dicionario contanto o valor que deve ser inserido a cada linha 
        """
        try:
            self.Header.SEQUENCEID  = header["seqId"]
            self.Header.NAMEALIAS   = header["name"]
            self.Header.DESCRIPTION = header["desc"]
            self.Header.ISDISABLE   = header["isdis"]
            self.Header.MINNUM      = header["minnum"]
            self.Header.MAXNUM      = header["maxnum"]
            self.Header.PREVNUM     = header["minnum"] - 1
            self.Header.CURNUM      = header["minnum"]
            self.Header.NEXTNUM     = header["minnum"] + 1
            self.Header.insert()
            self.Header.select().where(self.Header.SEQUENCEID == header.seqId and self.Header.NAMEALIAS == header.name)

            for each in lines:
                self.Lines.REFRECID  = self.Header.RECID.value
                if each["partType"] == int: #TODO: colocar o ENUM pra usar de alfaNum para poder arrumar o padding
                    self.Lines.PIECETYPE = each["partType"]
                    self.Lines.LINENUM   = each["place"]
                else:
                    self.Lines.PIECETYPE = each["partType"]
                    self.Lines.SEQPIECE  = each["part"]
                    self.Lines.LINENUM   = each["place"]
                self.Lines.insert()

            return {"status": True, "message": "Sequence created susscefully"}    
        except Exception as e:
            print("error: ", e)
            return {"status": False, "message": f"Unable to create due to: {e}"}
    
    def updateNumberSequence(self, reference:int, changes: dict):
        """
            Função para atualizar um ou mais valores de uma sequencia numerica
        """
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines, 'INNER').on(self.Header.RECID == self.Lines.REFRECID)
            if self.Header.rowcount() == 0 or self.Lines.rowcount() == 0:
                return {"status": False, "message": "No sequence found"}
            
            return {"status": True, "message": ""}
        except Exception as e:
            print("erro: ", e)
            return {"status": False, "message": f"Unable to update due to: {e}"}

    def deleteNumberSequence(self):
        """
            Função para excluir a sequencia numerica 
        """
        print("placeholder")

    def resetNumberSequence(self):
        """
            Função para reiniciar os valores da sequencia numerica
        """
        print("placeholder")

#[END CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {02/03/2026}