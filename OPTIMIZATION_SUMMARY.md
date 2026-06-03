# Spreadsheet Editing Optimization - v1.1.1

## Issues Addressed

### 1. Models Struggling with Spreadsheet Operations
**Problem:** Even large models (30B+ like Granite) had difficulty editing CSV and Excel files correctly.

**Root Cause:** 
- Insufficient guidance in tool descriptions
- No concrete examples of JSON operations
- Missing step-by-step workflow in system message

**Solution Implemented:**
- Enhanced `write_document` tool description with concrete JSON examples
- Added dedicated "Spreadsheet editing workflow" section to system message
- Included examples for all common operations (set_cell, append_row, set_column)
- Clarified column reference formats (letters vs. numbers)
- Emphasized the critical "read first" pattern

### 2. Confusing PDF Error Messages
**Problem:** When asked to "touch" or create a PDF file, error message was unclear about limitations.

**Root Cause:**
- Generic error message didn't explain what WAS possible
- No guidance on alternatives

**Solution Implemented:**
- Updated PDF error message to clearly state PDFs are read-only
- Explained that PDFs can be read but not created/edited
- Provided 3 concrete alternatives for users who need PDF functionality

## Changes Made

### File: `src/slice/chat.py`

#### Enhanced Tool Description (lines 56-95)
```python
"description": (
    "Write to document files (Word, Excel, PowerPoint, CSV, text). CANNOT create/edit PDFs.\n\n"
    "SPREADSHEET EXAMPLES:\n"
    "Excel/CSV operations use JSON with 'type' and parameters.\n\n"
    "To set a specific cell:\n"
    '{"type": "set_cell", "sheet": "Sheet1", "row": 5, "col": 3, "value": "Data"}\n'
    # ... more examples
)
```

#### Enhanced System Message (lines 122-154)
Added new section:
```python
"Spreadsheet editing workflow (Excel .xlsx, CSV .csv):\n"
"1. ALWAYS read the file first with read_document to see current structure\n"
"2. Identify what needs to change (which rows, columns, cells)\n"
"3. Use write_document with JSON operations\n"
"4. Common operations:\n"
"   - Set specific cell: {...}\n"
"   - Add new row: {...}\n"
"   - Fill column: {...}\n"
# ... complete workflow
```

### File: `src/slice/document_writer.py`

#### Improved PDF Error Message (lines 64-73)
```python
"error": (
    "PDF files cannot be created or edited with write_document - PDFs are read-only in Slice. "
    "You can read PDFs with read_document, but cannot write to them. "
    "Alternatives: (1) Convert to Word/Excel for editing, (2) Use external PDF tools, "
    "(3) Create content in Word/Excel then convert to PDF externally."
)
```

### File: `CLAUDE.md`

#### Updated System Message Guidelines
- Added complete "Spreadsheet editing workflow" section with 8-step guide
- Added "PDF handling" section explaining read-only limitation
- Updated "File operation rules" to clarify when to use touch vs. write_document
- Added item #7 to "Common Pitfalls" about spreadsheet operation confusion

## Expected Improvements

### For Spreadsheet Editing:
1. **Better success rate** - Models now have concrete examples to follow
2. **Fewer errors** - Step-by-step workflow reduces trial-and-error
3. **Correct JSON format** - Examples show exact syntax expected
4. **Read-first pattern** - Models will understand current state before editing
5. **Clear column references** - Models can use letters (A, M) or numbers (1, 13)

### For PDF Handling:
1. **Clear error messages** - Users understand why PDFs can't be edited
2. **Actionable alternatives** - Three concrete options provided
3. **No confusion about "touch"** - Clear that PDFs require special structure

## Testing Recommendations

Test with these prompts to verify improvements:

```
# Test 1: Simple cell update
"Read test.csv and change the value in row 2, column 3 to 'Updated'"

# Test 2: Add row to existing spreadsheet
"Read data.xlsx and add a new row with values: John, 30, Engineer"

# Test 3: Fill column with values
"Read budget.xlsx and fill column M starting at row 3 with values: 100, 200, 300"

# Test 4: Multiple operations
"Read sales.csv and: (1) update cell A1 to 'Product', (2) add a new row with Q1, Q2, Q3"

# Test 5: PDF limitation handling
"Create a new file called report.pdf"
# Should get clear error with alternatives
```

## Model Compatibility

These improvements benefit ALL models, but especially:
- **Smaller models** (7B-13B) - Now have concrete examples to reference
- **Mid-size models** (13B-30B) - Step-by-step workflow reduces confusion
- **Instruction-tuned models** - Better follow structured guidance

The enhanced tool descriptions work within Ollama's function calling framework, so no changes to model files needed.

## Version Update

Recommend bumping version to **v1.1.1** to reflect these optimizations:
- v1.1.0: Pure Python architecture
- v1.1.1: Spreadsheet editing optimizations + PDF clarity improvements
