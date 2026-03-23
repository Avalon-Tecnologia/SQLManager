import traceback

class NumberSequenceController:

    def __init__(self, Head, Line, seqTypes):
        self.Header     = Head
        self.Lines      = Line
        self.seqTypes   = seqTypes

    def getNextNum(self, reference: int) -> str:
        """
        Obtém o próximo número formatado da sequência.
        
        Recupera os dados da sequência (header e linhas) a partir do RECID
        e retorna o próximo número a ser utilizado no formato correto.
        
        Args:
            reference (int): O RECID (Record ID) da sequência desejada.
        
        Returns:
            str|dict: String contendo o número formatado conforme a sequência,
                     ou dicionário com mensagem de erro {'message': str}
                     se referência for zero ou sequência não encontrada.
        
        Example:
            >>> next_number = self.getNextNum(1)
            >>> if isinstance(next_number, str):
            ...     print(f'Próximo número: {next_number}')
            ... else:
            ...     print(f'Erro: {next_number["message"]}')
        
        Note:
            - Retorna erro se reference == 0
            - Retorna erro se sequência não existir
            - O padding (preenchimento com zeros) é calculado automaticamente
        """
        try:
            if reference == 0:
                return {"message": "Reference cannot be zero"}
            
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines).on(self.Header.RECID == self.Lines.REFRECID).execute()
            if not self.Header.records or not self.Lines.records:
                return {"message": "Sequence not found"}
            
            pad = len(str(self.Header.MAXNUM))

            return self.formatSequence(self.Lines.records, self.Header.CURNUM.value, pad)
        except Exception as e:
            traceback.print_exc()
            return {"status": False, "message": f"Unable to use due to: {e}"}
    
    def confirmUse(self, reference: int) -> dict:
        """
        Confirma o uso da sequência numérica e avança seus contadores.
        
        Marca o número atual como utilizado, atualizando PREVNUM, CURNUM e NEXTNUM
        para os próximos valores. Essencial para controlar a sequência de números.
        
        Args:
            reference (int): O RECID (Record ID) da sequência a ser confirmada.
        
        Returns:
            dict: Resultado da operação com as seguintes keys:
                - status (bool): True se confirmação bem-sucedida, False caso contrário
                - message (str): Mensagem descritiva do resultado ou erro
        
        Raises:
            Exception: Exceções são capturadas internamente e retornadas 
                      no dicionário de resposta com status False.
        
        Example:
            >>> result = self.confirmUse(1)
            >>> if result['status']:
            ...     print('Uso confirmado e contadores atualizados')
            ... else:
            ...     print(f'Erro: {result["message"]}')
        
        Note:
            - Retorna erro se reference == 0
            - Retorna erro se sequência não existir
            - Atualiza automaticamente os valores: PREVNUM <- CURNUM, CURNUM <- NEXTNUM
        """

        if reference == 0:
            return {"message": "Reference cannot be zero"}
        
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines).on(self.Header.RECID == self.Lines.REFRECID).order_by(self.Lines.LINENUM).execute()
            if not self.Header.records or not self.Lines.records:
                return {"message": "Sequence not found"}
            
            nextNum = self.Header.NEXTNUM.value
            self.Header.SelectForUpdate(True)

            self.Header.PREVNUM = self.Header.CURNUM.value
            self.Header.CURNUM = nextNum
            self.Header.NEXTNUM = nextNum + 1

            self.Header.update()

            return {"status": True, "message": "Sequence use confirmed"}
        except Exception as e:
            traceback.print_exc()
            return {"status": False, "message": f"Unable to use due to: {e}"}

    def formatSequence(self, parts=None, number=1, padding=4) -> str:
        """
        Formata uma sequência numérica combinando partes fixas e numéricas.
        
        Combina as partes da sequência (constantes, separadores e valores numéricos)
        em uma string formatada de acordo com a configuração da sequência.
        
        Args:
            parts (list, optional): Lista de dicionários com as partes da sequência.
                Se None, utiliza self.Lines.records. Dicionários devem conter:
                - LINENUM (int): Posição (1-indexed) da parte
                - PIECETYPE (int): Tipo da parte (NUMERIC, CONSTANT, SEPARATOR)
                - SEQPIECE (str): Valor fixo (None para NUMERIC)
                Padrão: None
            
            number (int): O valor numérico a ser inserido nas partes de tipo NUMERIC.
                Padrão: 1
            
            padding (int): Número de dígitos para preencher o número com zeros à esquerda.
                Padrão: 4
        
        Returns:
            str|dict: String formatada da sequência, ou dicionário com erro
                     {'message': str} se não conseguir processar.
        
        Example:
            >>> parts = [
            ...     {'LINENUM': 1, 'PIECETYPE': 1, 'SEQPIECE': 'PED'},
            ...     {'LINENUM': 2, 'PIECETYPE': 2, 'SEQPIECE': '-'},
            ...     {'LINENUM': 3, 'PIECETYPE': 3, 'SEQPIECE': None}
            ... ]
            >>> formatted = self.formatSequence(parts, 123, 5)
            >>> print(formatted)  # Output: 'PED-00123'
        
        Note:
            - Se parts é None e self.Lines.records está vazio, retorna erro
            - O número é preenchido com zeros à esquerda até atingir padding
        """
        if parts == None:
            if not self.Lines.records:
                return {"message": "Unable to find a suitable sequence to formar"}
            print("formating stored sequence")    

        parts = self.Lines.records
        ret = [""] * len(parts)
        for each in parts:
            if each["PIECETYPE"] == self.seqTypes.ALPHANUMERIC.value: 
                ret[each["LINENUM"]-1] = str(number).rjust(padding, "0")
            else:
                ret[each["LINENUM"]-1] = each["SEQPIECE"]
        
        return "".join(ret)

    def createNumberSequence(self, header: dict, lines: list) -> dict:
        """
        Cria uma nova sequência numérica no banco de dados.
        
        Realiza a inserção do cabeçalho e das linhas na tabela de sequências numéricas.
        O cabeçalho contém informações gerais (ID, nome, descrição, limites numéricos).
        As linhas contêm as partes/peças que compõem o formato da sequência.
        A sequência é validada quanto ao comprimento máximo permitido (20 caracteres).
        
        Args:
            header (dict): Dicionário com os valores do cabeçalho da sequência.
                Chaves obrigatórias:
                
                - seqId (str): Identificador único da sequência
                - name (str): Nome/alias da sequência
                - desc (str): Descrição da sequência
                - isdis (int): Estado (1 = desativado, 0 = ativado)
                - minnum (int): Quantidade numérica mínima da sequência
                - maxnum (int): Quantidade numérica máxima da sequência
            
            lines (list): Lista de dicionários com as partes que compõem a sequência.
                Cada dicionário deve conter:
                
                - pieceType (int): Tipo da parte (consulte SequenceTypes enum)
                - piece (str): Valor fixo da parte (None para tipo NUMERIC)
                - place (int): Posição (1-indexed) dentro da sequência
        
        Returns:
            dict: Resultado da operação com as seguintes keys:
                - status (bool): True se criação bem-sucedida, False caso contrário
                - message (str): Mensagem descritiva do resultado ou erro
        
        Raises:
            Exception: Exceções são capturadas internamente e retornadas 
                      no dicionário de resposta com status False.
        
        Example:
            >>> header = {
            ...     'seqId': 'PEDIDOS',
            ...     'name': 'Sequência de Pedidos',
            ...     'desc': 'Sequência numérica para pedidos de vendas',
            ...     'isdis': 0,
            ...     'minnum': 1,
            ...     'maxnum': 9999
            ... }
            >>> lines = [
            ...     {'pieceType': 1, 'piece': 'PED', 'place': 1},
            ...     {'pieceType': 2, 'piece': '-', 'place': 2},
            ...     {'pieceType': 3, 'piece': None, 'place': 3}
            ... ]
            >>> result = self.createNumberSequence(header, lines)
            >>> if result['status']:
            ...     print('Sequência criada com sucesso')
        
        Note:
            - PREVNUM é automaticamente set para minnum - 1
            - CURNUM é automaticamente set para minnum
            - NEXTNUM é automaticamente set para minnum + 1
            - Sequência será deletada se exceder 20 caracteres de comprimento total
        """
        try:
            self.Header.SEQUENCEID  = header["SEQUENCEID"]
            self.Header.NAMEALIAS   = header["NAMEALIAS"]
            self.Header.DESCRIPTION = header["DESCRIPTION"]
            self.Header.ISDISABLE   = header.get("ISDISABLE", 0)
            self.Header.MINNUM      = header["MINNUM"]
            self.Header.MAXNUM      = header["MAXNUM"]
            self.Header.PREVNUM     = header["MINNUM"] - 1
            self.Header.CURNUM      = header["MINNUM"]
            self.Header.NEXTNUM     = header["MINNUM"] + 1
            self.Header.insert()
            #self.Header.select().where(self.Header.SEQUENCEID == header["seqId"] and self.Header.NAMEALIAS == header["name"]).execute()

            for each in lines:
                self.Lines.REFRECID  = self.Header.RECID.value
                if self.seqTypes.find_by_value(each["PIECETYPE"]) == self.seqTypes.ALPHANUMERIC.value: #TODO: colocar o ENUM pra usar de alfaNum para poder arrumar o padding
                    self.Lines.PIECETYPE = self.seqTypes.find_by_value(each["PIECETYPE"])
                    self.Lines.SEQPIECE  = None
                    self.Lines.LINENUM   = each["LINENUM"]
                else:
                    self.Lines.PIECETYPE = self.seqTypes.find_by_value(each["PIECETYPE"])
                    self.Lines.SEQPIECE  = each["SEQPIECE"]
                    self.Lines.LINENUM   = each["LINENUM"]

                self.Lines.insert()
            self.Lines.select().where(self.Lines.REFRECID == self.Header.RECID.value).execute()
            test = self.formatSequence(self.Lines.records, 1, len(str(header['MAXNUM'])))
            if(len(test) > 20):
                self.deleteNumberSequence(self.Header.RECID.value)
                return{"status": False, "message": "Sequence exceeds character limit of 20"}
            return {"status": True, "message": "Sequence created suscefully"}    
        except Exception as e:
            traceback.print_exc()
            return {"status": False, "message": f"Unable to create due to: {e}"}
    
    def updateNumberSequence(self, reference: int, changes: dict) -> dict:
        """
        Atualiza valores de uma sequência numérica existente.
        
        Realiza a atualização dos dados de cabeçalho e linhas de uma sequência numérica.
        O cabeçalho contém informações gerais (ID, nome, descrição, limites numéricos).
        As linhas contêm as partes/peças que compõem o formato da sequência.
        
        Args:
            reference (int): O RECID (Record ID) da Header que será atualizada.
            changes (dict): Dicionário com as mudanças a serem aplicadas.
                Chaves devem estar em MAIÚSCULO. Não é recomendado alterar a ordem 
                da sequência. Chaves aceitas:
                
                - SEQUENCEID (str): Identificador único da sequência
                - NAMEALIAS (str): Nome/alias da sequência
                - DESCRIPTION (str): Descrição da sequência
                - ISDISABLE (bool): Estado da sequência (1 = desativado, 0 = ativado)
                - MINNUM (int): Valor numérico mínimo da sequência
                - MAXNUM (int): Valor numérico máximo da sequência
                - PREVNUM (int): Número anterior (opcional)
                - CURNUM (int): Número atual (opcional)
                - NEXTNUM (int): Próximo número (opcional)
                - lines (list): Lista de dicionários com as partes da sequência:
                    - LINENUM (int): Posição da parte na sequência
                    - PIECETYPE (int): Tipo da parte (constante, separador, numérico)
                    - SEQPIECE (str): Valor fixo da parte (None se for tipo NUMERIC)
        
        Returns:
            dict: Resultado da operação com as seguintes keys:
                - status (bool): True se atualização bem-sucedida, False caso contrário
                - message (str): Mensagem descritiva do resultado ou erro
        
        Raises:
            Exception: Exceções são capturadas internamente e retornadas 
                      no dicionário de resposta com status False.
        
        Example:
            >>> changes = {
            ...     'NAMEALIAS': 'NovaSequencia',
            ...     'DESCRIPTION': 'Descrição atualizada',
            ...     'MAXNUM': 9999,
            ...     'lines': [
            ...         {'LINENUM': 1, 'PIECETYPE': 1, 'SEQPIECE': 'PREFIX'},
            ...         {'LINENUM': 2, 'PIECETYPE': 3, 'SEQPIECE': None}
            ...     ]
            ... }
            >>> result = self.updateNumberSequence(1, changes)
            >>> if result['status']:
            ...     print('Sequência atualizada com sucesso')
        
        Note:
            Validação: Retorna erro se a sequência (RECID) não existir.
            Se lista de linhas está vazia, retorna erro sem fazer alterações.
        """
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines, 'INNER').on(self.Header.RECID == self.Lines.REFRECID).execute()
            if not self.Header.records or not self.Lines.records:
                return {"status": False, "message": "No sequence found"}
            self.Header.SelectForUpdate(True)
            self.Header.SEQUENCEID  = changes["HEAD"].get("SEQUENCEID"   , self.Header.SEQUENCEID)
            self.Header.NAMEALIAS   = changes["HEAD"].get("NAMEALIAS"    , self.Header.NAMEALIAS)
            self.Header.DESCRIPTION = changes["HEAD"].get("DESCRIPTION"    , self.Header.DESCRIPTION)
            self.Header.ISDISABLE   = changes["HEAD"].get("ISDISABLE"   , self.Header.ISDISABLE)
            self.Header.MINNUM      = changes["HEAD"].get("MINNUM"  , self.Header.MINNUM)
            self.Header.MAXNUM      = changes["HEAD"].get("MAXNUM"  , self.Header.MAXNUM)
            self.Header.PREVNUM     = changes["HEAD"].get("PREVNUM" , self.Header.PREVNUM)
            self.Header.CURNUM      = changes["HEAD"].get("CURNUM"  , self.Header.CURNUM)
            self.Header.NEXTNUM     = changes["HEAD"].get("NEXTNUM" , self.Header.NEXTNUM)  
            self.Header.update()

            if changes["LINES"] and len(changes["LINES"]) != 0:
                for each in changes["LINES"]:
                    self.Lines.select().where((self.Lines.REFRECID == reference) & (self.Lines.LINENUM == each["LINENUM"])).execute()
                    if(self.Lines.PIECETYPE != self.seqTypes.find_by_value(each["PIECETYPE"]) or
                       self.Lines.SEQPIECE != each["SEQPIECE"] or
                       self.Lines.LINENUM != each["LINENUM"]):
                        self.Lines.SelectForUpdate(True)

                        if each["PIECETYPE"] == self.seqTypes.ALPHANUMERIC.value:
                            self.Lines.PIECETYPE = self.seqTypes.find_by_value(each["PIECETYPE"])
                            self.Lines.SEQPIECE = None
                            self.Lines.LINENUM = each["LINENUM"]
                        else:
                            self.Lines.PIECETYPE = self.seqTypes.find_by_value(each["PIECETYPE"])
                            self.Lines.SEQPIECE = each["SEQPIECE"]
                            self.Lines.LINENUM = each["LINENUM"]

                        self.Lines.update()
            return {"status": True, "message": "update made suscessfully"}
        except Exception as e:
            traceback.print_exc()
            return {"status": False, "message": f"Unable to update due to: {e}"}

    def deleteNumberSequence(self, reference: int) -> dict:
        """
        Remove uma sequência numérica completa do banco de dados.
        
        Exclui tanto o registro de cabeçalho quanto todas as linhas associadas
        da sequência numérica identificada pelo RECID.
        
        Args:
            reference (int): O RECID (Record ID) da sequência a ser removida.
        
        Returns:
            dict: Resultado da operação com as seguintes keys:
                - status (bool): True se exclusão bem-sucedida, False caso contrário
                - message (str): Mensagem descritiva do resultado ou erro
        
        Raises:
            Exception: Exceções são capturadas internamente e retornadas 
                      no dicionário de resposta com status False.
        
        Example:
            >>> result = self.deleteNumberSequence(5)
            >>> if result['status']:
            ...     print('Sequência removida do banco de dados')
            ... else:
            ...     print(f'Erro ao remover: {result["message"]}')
        
        Note:
            - Retorna erro se reference == 0 ou reference for falsy
            - Retorna erro se sequência não existir
            - Remove todas as linhas antes de remover o cabeçalho
        """
        if reference == 0 or not reference:
            return {"status": False, "message": "invalid reference"}
        
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines, 'INNER').on(self.Header.RECID == self.Lines.REFRECID).execute()
            if not self.Header.records or not self.Lines.records:
                return{"status": False, "message": "no sequence found"}
            
            for each in self.Lines.records:
                self.Lines.set_current(each)
                self.Lines.delete()

            self.Header.delete()
            return {"status": True, "message": "sequence deleted from database"}
        except Exception as e:
            traceback.print_exc()
            return {"status": False, "message": f"Unable to delete due to: {e}"}

    def resetNumberSequence(self, reference: int) -> dict:
        """
            Função para reiniciar os valores da sequencia numerica

            Reinicia a contagem da parte numerica da sequencia numerica
            Resetar a sequencia pode acarretar a erros de pesquisa no banco
            devido a sobreposição de sequencias

            Args:
                reference (int): O RECID (Record ID) da sequencia a ser reiniciada

            Returns:
                dict: Resultado da operação com as seguintes keys:
                - status (bool): True se exclusão bem-sucedida, False caso contrário
                - message (str): Mensagem descritiva do resultado ou erro

            Raises:
            Exception: Exceções são capturadas internamente e retornadas 
                        no dicionário de resposta com status False.

            Example:
            >>> result = self.resetNumberSequence(5)
            >>> if result['status']:
            ...     print('Sequência reiniciada no banco de dados')
            ... else:
            ...     print(f'Erro ao reiniciar: {result["message"]}')
        
            Note:
                - Retorna erro se reference == 0 ou reference for falsy
                - Retorna erro se sequência não existir
                - Reinicia os valores do cabeçalho
        """
        try:
            if reference == 0 or not reference:
                return {"status": False, "message": "invalid reference"}
            
            self.Header.select().where(self.Header.RECID == reference).execute()

            if self.Header.RECID == 0:
                return{"status": False, "message": "no sequence found"}
            
            self.Header.SelectForUpdate(True)
            self.Header.PREVNUM = self.Header.MINNUM.value - 1
            self.Header.CURNUM = self.Header.MINNUM.value
            self.Header.NEXTNUM = self.Header.MINNUM.value + 1
            self.Header.update()
            return {"status": True, "message": "sequence reset in database"}
        except Exception as e:
            traceback.print_exc()
            return {"status": False, "message": f"Unable to delete due to: {e}"}
