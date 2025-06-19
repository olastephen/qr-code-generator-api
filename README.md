# QR Code Generator API

A simple and customizable QR Code Generator API built with FastAPI and Python.

## Features
- Generate QR codes from text or URLs
- GET and POST endpoints
- Customizable QR code options (size, color, border, error correction, etc.)
- Support for PNG, SVG, and JPEG formats
- Downloadable filenames
- Return QR code as base64 string in JSON
- Decode QR codes from images
- Batch QR code generation (ZIP)
- QR code with logo/image overlay
- Artistic QR codes with custom colors (using segno)
- User-friendly error messages and validation

## Requirements
- Python 3.7+

## Installation
1. Clone the repository or download the code.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quickstart

1. **Start the API server:**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`.

2. **Generate a QR code (GET):**
   ```bash
   curl -o qr.png "http://127.0.0.1:8000/generate?data=HelloWorld"
   ```
   This saves a PNG QR code for "HelloWorld" as `qr.png`.

3. **Generate a QR code (POST, JSON):**
   ```bash
   curl -X POST "http://127.0.0.1:8000/generate" \
        -H "Content-Type: application/json" \
        -d '{"data": "https://example.com", "format": "svg"}' \
        -o qr.svg
   ```
   This saves a SVG QR code for "https://example.com" as `qr.svg`.

4. **Decode a QR code image:**
   ```bash
   curl -X POST "http://127.0.0.1:8000/decode" \
        -F "file=@qr.png"
   ```
   This will return the decoded data from `qr.png`.

---

## Running the API
Start the server with:
```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Usage

### 1. Generate QR Code (GET)
Generate a QR code with default options by passing data as a query parameter:

```
GET /generate?data=HelloWorld
```

**Options:**
- `data` (required): Data to encode
- `format`: png, svg, jpeg (default: png)
- `filename`: Download filename (optional)
- `base64`: If true, returns base64 string in JSON (optional)

**Example:**
```
GET /generate?data=HelloWorld&format=svg&filename=myqr&base64=true
```

### 2. Generate QR Code (POST)
Send a JSON payload to customize the QR code:

```
POST /generate
Content-Type: application/json

{
  "data": "https://example.com",
  "box_size": 8,
  "border": 2,
  "fill_color": "blue",
  "back_color": "yellow",
  "version": 2,
  "error_correction": "H",
  "format": "jpeg",
  "filename": "site",
  "base64": true
}
```

**Response:** PNG, SVG, or JPEG image, or JSON with base64 string.

### 3. Decode QR Code (POST)
Decode a QR code from an uploaded image (PNG or JPEG):

```
POST /decode
Content-Type: multipart/form-data
file: <your_qr_code.png>
```

**Response:**
```json
{
  "results": [
    { "data": "decoded text or URL", "type": "QRCODE" }
  ]
}
```

### 4. Batch QR Code Generation (POST)
Generate multiple QR codes and receive a ZIP file:

```
POST /batch_generate
Content-Type: application/json

{
  "items": [
    {"data": "https://example.com", "format": "png", "filename": "site"},
    {"data": "Hello World", "format": "svg"},
    {"data": "Another", "format": "jpeg", "filename": "another_qr"}
  ]
}
```

**Response:** ZIP file containing all QR codes.

### 5. Generate QR Code with Logo (POST)
Overlay a logo image in the center of the QR code:

```
POST /generate_with_logo
Content-Type: multipart/form-data

Fields:
- data: The data to encode (required)
- logo: The logo image file (PNG/JPEG, optional)
- box_size, border, fill_color, back_color, version, format, filename, base64 (optional)
```

**Example using curl:**
```bash
curl -X POST "http://127.0.0.1:8000/generate_with_logo" \
     -F "data=Hello with logo" \
     -F "logo=@logo.png" \
     -F "format=png" \
     -o qr_with_logo.png
```

#### Best Practices for QR Codes with Logos
- **Always use error correction level 'H'** (the API does this by default for logo QR codes). This allows up to 30% of the QR code to be obscured and still be readable.
- **Keep the logo small**: The logo should cover no more than 1/6 of the QR code area for best scan reliability.
- **Ensure good color contrast**: The QR code and logo should have strong contrast with each other and the background for easy scanning.

### 6. Generate Artistic QR Code (POST)
Create a QR code with custom colors and style using segno:

```
POST /generate_artistic
Content-Type: multipart/form-data

Fields:
- data: The data to encode (required)
- dark: Foreground color (default: #000)
- light: Background color (default: #fff)
- border: Border size (default: 4)
- scale: Size multiplier (default: 10)
- error_correction: L, M, Q, H (default: L)
- format: png or svg (default: png)
```

**Example using curl:**
```bash
curl -X POST "http://127.0.0.1:8000/generate_artistic" \
     -F "data=Artistic QR" \
     -F "dark=#1a73e8" \
     -F "light=#fffbe7" \
     -F "format=svg" \
     -o artistic_qr.svg
```

## Customization Options (POST)
| Field            | Type   | Default   | Description                                 |
|------------------|--------|-----------|---------------------------------------------|
| data             | string | required  | The data to encode in the QR code           |
| box_size         | int    | 10        | Size of each QR box                         |
| border           | int    | 4         | Border thickness                            |
| fill_color       | string | "black"   | Color of the QR code                        |
| back_color       | string | "white"   | Background color                            |
| version          | int    | 1         | QR code version (1-40)                      |
| error_correction | string | "L"       | Error correction: L, M, Q, or H             |
| format           | string | "png"     | Output format: png, svg, jpeg               |
| filename         | string |           | Download filename (optional)                |
| base64           | bool   | false     | Return as base64 string in JSON             |
| logo             | file   |           | Logo image for overlay (with_logo only)     |

## API Documentation
Interactive docs available at:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## License
MIT 