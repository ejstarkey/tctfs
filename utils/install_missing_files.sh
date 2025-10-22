#!/bin/bash
# TCTFS Missing Files Installation Script
# This script copies all created files to their proper locations

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base directory - modify this to your TCTFS path
TCTFS_DIR="${1:-$HOME/tctfs}"
OUTPUT_DIR="/mnt/user-data/outputs"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TCTFS Missing Files Installer${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Installing to: ${GREEN}${TCTFS_DIR}${NC}"
echo ""

# Check if TCTFS directory exists
if [ ! -d "$TCTFS_DIR" ]; then
    echo -e "${RED}Error: TCTFS directory not found at $TCTFS_DIR${NC}"
    echo "Usage: $0 [path_to_tctfs]"
    exit 1
fi

# Create directories if they don't exist
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$TCTFS_DIR/tctfs_app/utils"
mkdir -p "$TCTFS_DIR/tctfs_app/schemas"
mkdir -p "$TCTFS_DIR/tctfs_app/sockets"
mkdir -p "$TCTFS_DIR/tctfs_app/static/css"
mkdir -p "$TCTFS_DIR/tctfs_app/static/js"
mkdir -p "$TCTFS_DIR/tctfs_app/static/img"

# Function to copy file with status
copy_file() {
    local src=$1
    local dest=$2
    local name=$3
    
    if [ -f "$src" ]; then
        cp "$src" "$dest"
        echo -e "  ${GREEN}✓${NC} $name"
    else
        echo -e "  ${RED}✗${NC} $name (source not found)"
    fi
}

# Copy Utils
echo -e "\n${BLUE}Installing Utils...${NC}"
copy_file "$OUTPUT_DIR/utils__init__.py" "$TCTFS_DIR/tctfs_app/utils/__init__.py" "utils/__init__.py"
copy_file "$OUTPUT_DIR/utils_http.py" "$TCTFS_DIR/tctfs_app/utils/http.py" "utils/http.py"
copy_file "$OUTPUT_DIR/utils_parsing.py" "$TCTFS_DIR/tctfs_app/utils/parsing.py" "utils/parsing.py"
copy_file "$OUTPUT_DIR/utils_time.py" "$TCTFS_DIR/tctfs_app/utils/time.py" "utils/time.py"

# Copy Schemas
echo -e "\n${BLUE}Installing Schemas...${NC}"
copy_file "$OUTPUT_DIR/schemas__init__.py" "$TCTFS_DIR/tctfs_app/schemas/__init__.py" "schemas/__init__.py"
copy_file "$OUTPUT_DIR/schemas_storm.py" "$TCTFS_DIR/tctfs_app/schemas/storm.py" "schemas/storm.py"
copy_file "$OUTPUT_DIR/schemas_advisory.py" "$TCTFS_DIR/tctfs_app/schemas/advisory.py" "schemas/advisory.py"
copy_file "$OUTPUT_DIR/schemas_forecast.py" "$TCTFS_DIR/tctfs_app/schemas/forecast.py" "schemas/forecast.py"

# Copy Sockets
echo -e "\n${BLUE}Installing Sockets...${NC}"
copy_file "$OUTPUT_DIR/sockets__init__.py" "$TCTFS_DIR/tctfs_app/sockets/__init__.py" "sockets/__init__.py"

# Copy Static CSS
echo -e "\n${BLUE}Installing CSS...${NC}"
copy_file "$OUTPUT_DIR/static_css_dashboard.css" "$TCTFS_DIR/tctfs_app/static/css/dashboard.css" "css/dashboard.css"
copy_file "$OUTPUT_DIR/static_css_map.css" "$TCTFS_DIR/tctfs_app/static/css/map.css" "css/map.css"

# Copy Static JS
echo -e "\n${BLUE}Installing JavaScript...${NC}"
copy_file "$OUTPUT_DIR/static_js_dashboard.js" "$TCTFS_DIR/tctfs_app/static/js/dashboard.js" "js/dashboard.js"
copy_file "$OUTPUT_DIR/static_js_storm_map.js" "$TCTFS_DIR/tctfs_app/static/js/storm_map.js" "js/storm_map.js"
copy_file "$OUTPUT_DIR/static_js_zones_layer.js" "$TCTFS_DIR/tctfs_app/static/js/zones_layer.js" "js/zones_layer.js"
copy_file "$OUTPUT_DIR/static_js_sockets.js" "$TCTFS_DIR/tctfs_app/static/js/sockets.js" "js/sockets.js"
copy_file "$OUTPUT_DIR/static_js_time_controls.js" "$TCTFS_DIR/tctfs_app/static/js/time_controls.js" "js/time_controls.js"

# Copy Logo
echo -e "\n${BLUE}Installing Logo...${NC}"
copy_file "$OUTPUT_DIR/static_img_logo.svg" "$TCTFS_DIR/tctfs_app/static/img/logo.svg" "img/logo.svg"

# Verify no empty files remain
echo -e "\n${BLUE}Verifying installation...${NC}"
EMPTY_FILES=$(find "$TCTFS_DIR/tctfs_app" -type f -size 0 2>/dev/null | wc -l)

if [ "$EMPTY_FILES" -eq 0 ]; then
    echo -e "${GREEN}✓ No empty files found${NC}"
else
    echo -e "${RED}⚠ Warning: Found $EMPTY_FILES empty files${NC}"
    find "$TCTFS_DIR/tctfs_app" -type f -size 0
fi

# Set permissions
echo -e "\n${BLUE}Setting permissions...${NC}"
chmod -R u+rw "$TCTFS_DIR/tctfs_app/utils" 2>/dev/null || true
chmod -R u+rw "$TCTFS_DIR/tctfs_app/schemas" 2>/dev/null || true
chmod -R u+rw "$TCTFS_DIR/tctfs_app/sockets" 2>/dev/null || true
chmod -R u+rw "$TCTFS_DIR/tctfs_app/static" 2>/dev/null || true
echo -e "${GREEN}✓ Permissions set${NC}"

# Summary
echo -e "\n${BLUE}================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo "Files installed to: $TCTFS_DIR"
echo ""
echo -e "Next steps:"
echo -e "  1. Review ${GREEN}README_MISSING_FILES.md${NC} for usage examples"
echo -e "  2. Test imports: ${BLUE}python -c 'from tctfs_app.utils import utc_now'${NC}"
echo -e "  3. Run your application: ${BLUE}python wsgi.py${NC}"
echo ""
echo -e "${BLUE}Happy cyclone tracking! 🌀${NC}"
