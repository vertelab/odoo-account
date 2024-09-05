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

def document_rounding(x):

    if x >= 100:

        return int(math.floor(x / 100.0)) * 100
    else:
        return  x if int(math.floor(x / 100.0)) * 100 == 0 else int(math.floor(x / 100.0)) * 100

class invoice(BaseModel):

    invoice_number: int = Field(description="The invoice number")
    invoice_date: str = Field(description="The date the invoice was issued")
    order_date: list = Field(description="The date that the order was placed")
    due_date: str = Field(description="The due date on an invoice is the final deadline by which the payment is expected to be received")
    issuer: str = Field(description="The issuer of the invoice")
    recipient: str = Field(description="The recipient of the invoice")
    reference_number: int = Field(description="The reference number on an invoice is a unique identifier assigned to that specific document")
    customer_reference: str = Field(description="The customer reference on an invoice is a field used to identify the specific customer or project associated with the invoice")
    net_total: float = Field(description="The net total on an invoice is the total amount due after any discounts or deductions have been applied")
    vat: list = Field("VAT (Value Added Tax) is a consumption tax levied on the sale of most goods and services. It's a multi-stage tax, meaning it's added at each stage of the production and distribution process")
    gross_total: float = Field(description="The gross total on an invoice is the total amount of the goods or services before any discounts or deductions have been applied")
    rounding_adjustment: float = Field(description="Rounding Adjustments on an invoice refer to the minor differences that can occur due to rounding practices. When calculating prices, especially for items with decimal points, it's common to round the amounts to a certain number of decimal places. However, when adding up these rounded amounts, there can be a small discrepancy between the calculated total and the actual sum of the unrounded amounts.")
    amount_due: float = Field(description="The Amount Due on an invoice is the final amount that the customer is expected to pay. It's the total cost of the goods or services, including any taxes and fees, minus any discounts or credits that have been applied.")
    issuer_address: str = Field(description="The Issuer Address on an invoice is the address of the company or individual issuing the invoice. It's typically located in the header or footer of the document.")
    recipient_address: str = Field(description="The Recipient Address on an invoice is the address of the customer or individual who is receiving the invoice. It's typically located in the header or footer of the document.")
    organization_number: str = Field(description="The Organization Number (or Company Registration Number) on an invoice is a unique identifier assigned to a company or organization by the government. It's often used for tax purposes and to identify businesses in official records.")
    ocr_reference_number: int = Field(description="OCR stands for Optical Character Recognition. In the context of Swedish invoices, the OCR Reference Number is a specific format used to identify the invoice and facilitate automated payment processing. It's a standardized number that ensures smooth and efficient payments, particularly when using online banking or automated payment systems.")
    bankgiro: str = Field(description="Bankgiro is a Swedish payment system that provides a unique identification number for bank accounts. It's a common reference on invoices and other financial documents in Sweden.")
    services_and_charges: dict = Field(description="Services and Charges on an invoice list the specific goods or services provided and their corresponding costs. It's a breakdown of the items that make up the total amount due.")

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
