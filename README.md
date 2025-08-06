# Website Review Tool - Crowdsourced Edition

A fast, Tinder-like web interface for quickly reviewing and categorizing company websites from a CSV file. **Now with multi-user support for team collaboration!**

## 🌟 Key Features

- 🚀 **Fast Review Process**: Tinder-style interface for quick website evaluation
- 👥 **Multi-User Crowdsourcing**: Multiple team members can work simultaneously
- 🎯 **No Duplicates**: Smart assignment system ensures no two users review the same website
- 📊 **Real-Time Progress**: Live progress tracking visible to all users
- 💾 **Auto-Save & Resume**: Automatically saves progress and handles interruptions
- ⚡ **Keyboard Shortcuts**: Use G (Good) and B (Bad) for lightning-fast reviews
- 📱 **Responsive Design**: Works perfectly on desktop and mobile devices
- 📁 **CSV Export**: Export liked and disliked websites separately
- 🛠️ **Admin Dashboard**: Monitor team progress and export results
- ☁️ **Vercel Ready**: Deploy instantly to the cloud for team access

## 🚀 Quick Start

### For Team Collaboration (Recommended)

**Deploy to Vercel for instant team access:**

1. **Push to GitHub** and deploy to Vercel (see `DEPLOYMENT.md` for detailed instructions)
2. **Share the URL** with your team - no setup required for team members!
3. **Monitor progress** via the admin dashboard at `/admin`

### For Local Development

1. **Install Dependencies**:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. **Ensure your CSV file is ready**:
   - File should be named `b2c_failures_review.csv` 
   - Must contain columns: `company_name`, `website`

3. **Run the Application**:
   ```bash
   python3 app.py
   ```

4. **Access the interfaces**:
   - **Main Review**: `http://localhost:5001`
   - **Admin Dashboard**: `http://localhost:5001/admin`

## How to Use

### Main Interface
- **Website Display**: Each company's website is loaded in an iframe for quick preview
- **Action Buttons**: Click "Good Website" or "Bad Website" to categorize
- **Progress Bar**: Shows how many websites you've reviewed
- **Statistics Panel**: Real-time counts of liked/disliked websites

### Keyboard Shortcuts
- **G**: Mark current website as "Good"
- **B**: Mark current website as "Bad"  
- **O**: Open current website in a new tab for detailed review

### Export Options
- **Export Liked**: Download CSV of all websites you marked as good
- **Export Disliked**: Download CSV of all websites you marked as bad
- **Reset Progress**: Start over from the beginning (with confirmation)

## File Structure

```
tam-failure-classifier/
├── app.py                     # Flask backend application
├── templates/
│   └── index.html            # Web interface
├── b2c_failures_review.csv   # Your input CSV file
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── review_state.json         # Auto-generated progress file
├── liked_websites.csv        # Generated when exporting liked sites
└── disliked_websites.csv     # Generated when exporting disliked sites
```

## Persistence & Resume

The tool automatically saves your progress in `review_state.json`. If you:
- Close the browser
- Restart the application  
- Experience internet disconnection

Simply restart the app and navigate to `http://localhost:5000` - you'll resume exactly where you left off!

## CSV Requirements

Your input CSV must contain at least these columns:
- `company_name`: Name of the company
- `website`: URL of the company's website

Additional columns will be preserved in the exported files.

## Troubleshooting

### Website Won't Load in Frame
Some websites block iframe embedding for security. You can:
- Use the "O" keyboard shortcut to open in a new tab
- Make your decision based on the company name and URL

### Port Already in Use
If port 5000 is busy, modify the last line in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port number
```

### CSV Not Found
Ensure your CSV file is named exactly `b2c_failures_review.csv` and is in the same directory as `app.py`.

## Technical Details

- **Backend**: Flask (Python)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Data Storage**: JSON for progress, CSV for exports
- **Browser Compatibility**: Modern browsers with iframe support

Enjoy your fast website review process! 🚀