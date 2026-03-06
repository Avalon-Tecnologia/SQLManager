"""
Por meio deste arquivo adicionar todas as tabelas (Extended Data Types) que são chaves do SQLManager.
AVISO:
 - Tabelas presentes neste arquivo não são para a aplicação mas para o banco de dados.
"""

__all__ = [
    'Ensures',
]

Ensures = {
    "NumberSequenceTable": '''
[RECID] [bigint] IDENTITY(1,1) NOT NULL,
[SEQUENCEID] [nvarchar](10) NOT NULL,
[NAMEALIAS] [nvarchar](100) NOT NULL,
[DESCRIPTION] [nvarchar](200) NOT NULL,
[ISDISABLE] [bit] NOT NULL DEFAULT 0,
[PREVNUM] [int] NULL,
[CURNUM] [int] NULL,
[NEXTNUM] [int] NULL,
[MINNUM] [int] NOT NULL DEFAULT 1,
[MAXNUM] [int] NOT NULL DEFAULT 9999 CHECK([MAXNUM]>=(0) AND [MAXNUM]<=(99999999)),
[CREATEDATETIME] [datetime] NOT NULL DEFAULT SYSDATETIME(),
''',
    "NumberSequenceLine": '''
[RECID] [bigint] IDENTITY(1,1) NOT NULL,
[REFRECID] [bigint] NOT NULL,
[PIECETYPE] [int] NULL,
[SEQPIECE] [nvarchar](5) NULL,
[LINENUM] [int] NULL,
'''
}