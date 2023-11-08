import fitz  # PyMuPDF
import textstat
from collections import Counter
import csv
import json
import sys

def extract_chapters_and_text(pdf_path, chapter_starts):
    with fitz.open(pdf_path) as pdf:
        chapters = []
        for start in chapter_starts:
            page = pdf[start-1]
            text_blocks = page.get_text("blocks")
            chapter_title = ""
            for block in text_blocks:
                if block[4].strip(): 
                     # We found some text
                    chapter_title = block[4].strip().replace("\n", " ")
                    break  # Assume the first text block is the chapter title
            chapters.append({'title': chapter_title, 'text': '', 'start_page': start})

        # Append the end of the book as the last "start" to get the text of the last chapter
        chapter_starts.append(len(pdf))

        # Extract text for each chapter
        for i, chapter in enumerate(chapters):
            for page_num in range(chapter['start_page'], chapter_starts[i + 1]):
                page = pdf[page_num]
                chapters[i]['text'] += page.get_text()

    return chapters

def get_page_size(pdf, page_number):
    page = pdf[page_number]
    return page.rect.width, page.rect.height

def get_margin_widths(pdf, page_number):
    page = pdf[page_number]
    blocks = page.get_text("blocks")
    left_margin = min(block[0] for block in blocks)
    top_margin = min(block[1] for block in blocks)
    right_margin = page.rect.width - max(block[2] for block in blocks)
    bottom_margin = page.rect.height - max(block[3] for block in blocks)
    return left_margin, top_margin, right_margin, bottom_margin

def get_most_common_font(pdf, page_number):
    page = pdf[page_number]
    text_instances = page.get_text("dict")["blocks"]
    fonts = []
    for instance in text_instances:
        for line in instance["lines"]:
            for span in line["spans"]:
                fonts.append((span['font'], span['size']))
    most_common_font = Counter(fonts).most_common(1)
    return most_common_font[0][0] if most_common_font else (None, None)

def analyze_chapter(text):
    # Analyze the given text and return a dictionary of readability scores
    return {
        'flesch_reading_ease': textstat.flesch_reading_ease(text),
        'smog_index': textstat.smog_index(text),
        'flesch_kincaid_grade': textstat.flesch_kincaid_grade(text),
        'coleman_liau_index': textstat.coleman_liau_index(text),
        'automated_readability_index': textstat.automated_readability_index(text),
        'dale_chall_readability_score': textstat.dale_chall_readability_score(text),
        'difficult_words': textstat.difficult_words(text),
        'linsear_write_formula': textstat.linsear_write_formula(text),
        'gunning_fog': textstat.gunning_fog(text),
        'text_standard': textstat.text_standard(text, float_output=True)
    }

def output_to_csv(book_analysis, csv_path):
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Filename', csv_path])
        writer.writerow(['Chapters', len(book_analysis['chapters'])])
        writer.writerow(['Images', book_analysis['total_images']])
        writer.writerow(['Pages', book_analysis['total_pages']])
        writer.writerow(['Most Common Font', book_analysis['most_common_font']])
        writer.writerow(['Average Readability Score', book_analysis['average_readability_score']])
        #write an empty row
        writer.writerow([])
                        
        # Write the header
        writer.writerow(['Chapter Title', 'Flesch Reading Ease', 'SMOG Index', 'Flesch-Kincaid Grade', 'Coleman-Liau Index', 'ARI', 'Dale-Chall Score', 'Difficult Words', 'Linsear Write Formula', 'Gunning Fog', 'Text Standard'])

        # Write the data for each chapter
        for chapter in book_analysis['chapters']:
            writer.writerow([
                chapter['title'],
                chapter['flesch_reading_ease'],
                chapter['smog_index'],
                chapter['flesch_kincaid_grade'],
                chapter['coleman_liau_index'],
                chapter['automated_readability_index'],
                chapter['dale_chall_readability_score'],
                chapter['difficult_words'],
                chapter['linsear_write_formula'],
                chapter['gunning_fog'],
                chapter['text_standard']
            ])

def count_images_per_chapter(pdf, chapter_starts):
    images_per_chapter = []
    current_chapter = 0
    for page_num in range(len(pdf)):
        if current_chapter < len(chapter_starts) - 1 and page_num >= chapter_starts[current_chapter + 1]:
            current_chapter += 1
        page = pdf[page_num]
        images = page.get_images(full=True)
        if len(images_per_chapter) <= current_chapter:
            images_per_chapter.append(0)
        images_per_chapter[current_chapter] += len(images)
    return images_per_chapter

def extract_text_from_pdf(pdf_path):
    # Open the PDF file
    with fitz.open(pdf_path) as pdf:
        text = [page.get_text() for page in pdf]
    return text

# Main function to extract text, analyze, and output to CSV
def main(pdf_path, csv_path, chapter_starts):
    # Extract chapters and text from the PDF
    chapters = extract_chapters_and_text(pdf_path, chapter_starts)
    book_text = extract_text_from_pdf(pdf_path)
    pdf_file = fitz.open(pdf_path)
    images_per_chapter = count_images_per_chapter(pdf_file, chapter_starts)
    most_common_font = get_most_common_font(pdf_file, chapter_starts[0])
    pdf_file.close()

    # Initialize book analysis with chapter titles
    book_analysis = {
        'total_pages': len(book_text),
        'total_images': sum(images_per_chapter),
        'readability_scores': [],
        'average_readability_score': 0,
        'chapters': []
    }


    # Analyze each chapter
    for chapter in chapters:
        chapter_analysis = analyze_chapter(chapter['text'])
        chapter_analysis['title'] = chapter['title']
        book_analysis['chapters'].append(chapter_analysis)

    

    tot_images = 0
    for i in range(len(book_analysis['chapters'])):
        book_analysis['chapters'][i]['images'] = images_per_chapter[i]
        tot_images += images_per_chapter[i]
    book_analysis['images'] = tot_images
    book_analysis['most_common_font'] = most_common_font
    book_analysis['average_readability_score'] = sum(score['flesch_reading_ease'] for score in book_analysis['chapters']) / len(book_analysis['chapters'])

    
    # Output the analysis to a CSV file
    output_to_csv(book_analysis, csv_path)
    # Print the analysis to the console
    print(json.dumps(book_analysis, indent=4))

#rewrite the __main__ function to take the pdf file path and the chapter starts from a config file


if __name__ == "__main__":

    pdf_file_path = ''  # Replace with the path to your PDF file
    csv_output_path = pdf_file_path + '.csv'  # Replace with your desired CSV output path

    chapter_starts = []
    main(pdf_file_path, csv_output_path, chapter_starts)
