import json
import logging
import base64
import numpy as np
from sentence_transformers import SentenceTransformer


from odoo import models, fields, api, _
from odoo.exceptions import MissingError, AccessError, UserError

_logger = logging.getLogger(__name__)

import os, datetime, math


from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser



class AccountInvoice(models.Model):
    _inherit = 'account.move'

    scan_llm_json = fields.Text(string='Scan Json')

    def pdf_loader(self,file_path):

        loader = PyPDFLoader(file_path=file_path,extraction_mode="layout")

        documents = loader.load()

        return documents

    def print_invoice(documents):

        full_document = ""

        for doc in documents:
            doc_lenght = document_rounding(len(doc.page_content.strip()))
            full_document = f"{full_document}\n{doc.page_content.strip()[:doc_lenght]}"

        print(full_document) 

    def ai_text_spliter(documents):

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_documents = text_splitter.split_documents(documents)

        return split_documents

    def ai_templet_prompt():

        system_prompt =\
        """
        {context}

        ---

        Given the context above, put the relevant values in the JSON format bellow. If you cant finde the relevant values, put false as the anwser.

        ---

        {json_format}
        
        ---
        
        Answer: 
        """.strip()

        prompt = PromptTemplate(
            template=system_prompt,
            input_variables=["context"],
            partial_variables={"json_format": JsonOutputParser(pydantic_object=invoice).get_format_instructions()},
        )
        
        return prompt

    def setup_vectorstore(documents, embedding):

        vectorstore = FAISS.from_documents(documents=documents, embedding=embedding)
        retriever = vectorstore.as_retriever()

        return retriever

    def setup_rag_chain(llm, prompt, retriever):

        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        return rag_chain

    def call_on_ai(rag_chain, chat_input):

        results = rag_chain.invoke({"input": f"{chat_input}"})

        return results["answer"]

    if _scan_llm == "__main__":    

        os.environ["OPENAI_API_KEY"] = input("Enter API key: ")
        llm = ChatOpenAI(model="gpt-4o")

        file_path = Path(input("path: "))
        # chat_input = input("Ställ frågor om fakturan: ")
        chat_input = "Give me a summary of the invoice"

        documents = pdf_loader(file_path=file_path)

        print_invoice(documents=documents)

        split_documents = ai_text_spliter(documents)

        prompt = ai_templet_prompt()

        retriever = setup_vectorstore(documents=documents,embedding=HuggingFaceEmbeddings())

        rag_chain = setup_rag_chain(llm=llm,prompt=prompt,retriever=retriever)

        answer = call_on_ai(rag_chain=rag_chain,chat_input=chat_input)

        print(answer)




class ResPartner(models.Model):
    _inherit = 'res.partner'

    scan_llm_vector = fields.Binary(string='_')


    @api.model
    def create_rag_odoo_models(self,type,name="Odoo Models RAG"):
        # Initialize the sentence transformer model
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Extract model and field information
        ir_model = self.env['ir.model']
        models_data = []
        for odoo_model in ir_model.search([]):
            model_info = f"Model: {odoo_model.name} ({odoo_model.model})"
            fields_info = []
            for field in odoo_model.field_id:
                field_info = f"Field: {field.name} ({field.ttype})"
                fields_info.append(field_info)
            
            models_data.append(model_info + "\n" + "\n".join(fields_info))

        # Create embeddings
        embeddings = model.encode(models_data)

        # Serialize the embeddings
        serialized_data = {
            'embeddings': base64.b64encode(embeddings.tobytes()).decode('utf-8'),
            'shape': embeddings.shape
        }

        # Create a record in the odoo.rag model
        self.create({
            'name': self.name,
            'rag_data': json.dumps(serialized_data)
        })

    @api.model
    def load_rag(self,name="Odoo Models RAG"):
        rag_record = self.search([('name', '=', name)], limit=1)
        if rag_record:
            serialized_data = json.loads(rag_record.rag_data)
            embeddings = np.frombuffer(base64.b64decode(serialized_data['embeddings']), dtype=np.float32).reshape(serialized_data['shape'])
            return embeddings
        return None
        



def pdf_loader(file_path):

    loader = PyPDFLoader(file_path=file_path,extraction_mode="layout")

    documents = loader.load()

    return documents

def print_invoice(documents):

    full_document = ""

    for doc in documents:
        doc_lenght = document_rounding(len(doc.page_content.strip()))
        full_document = f"{full_document}\n{doc.page_content.strip()[:doc_lenght]}"

    print(full_document) 

def ai_text_spliter(documents):

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_documents = text_splitter.split_documents(documents)

    return split_documents

def ai_templet_prompt():

    system_prompt =\
    """
    {context}

    ---

    Given the context above, put the relevant values in the JSON format bellow. If you cant finde the relevant values, put false as the anwser.

    ---

    {json_format}
    
    ---
    
    Answer: 
    """.strip()

    prompt = PromptTemplate(
        template=system_prompt,
        input_variables=["context"],
        partial_variables={"json_format": JsonOutputParser(pydantic_object=invoice).get_format_instructions()},
    )
    
    return prompt

def setup_vectorstore(documents, embedding):

    vectorstore = FAISS.from_documents(documents=documents, embedding=embedding)
    retriever = vectorstore.as_retriever()

    return retriever

def setup_rag_chain(llm, prompt, retriever):

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain

def call_on_ai(rag_chain, chat_input):

    results = rag_chain.invoke({"input": f"{chat_input}"})

    return results["answer"]

if __name__ == "__main__":    

    os.environ["OPENAI_API_KEY"] = input("Enter API key: ")
    llm = ChatOpenAI(model="gpt-4o")

    file_path = Path(input("path: "))
    # chat_input = input("Ställ frågor om fakturan: ")
    chat_input = "Give me a summary of the invoice"

    documents = pdf_loader(file_path=file_path)

    print_invoice(documents=documents)

    split_documents = ai_text_spliter(documents)

    prompt = ai_templet_prompt()

    retriever = setup_vectorstore(documents=documents,embedding=HuggingFaceEmbeddings())

    rag_chain = setup_rag_chain(llm=llm,prompt=prompt,retriever=retriever)

    answer = call_on_ai(rag_chain=rag_chain,chat_input=chat_input)

    print(answer)
