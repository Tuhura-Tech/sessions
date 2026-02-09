# Email Templates

This directory contains all HTML and text email templates used by the Tūhura platform.

## Branding & Design

All email templates follow a consistent brand identity:

### Color Palette
- **Primary Green**: `#6aa469` - Used for call-to-action buttons and accents
- **Primary Blue**: `#175b98` - Used in gradient headers and highlights
- **Background**: `#f4f7fa` - Light background for info boxes and footers
- **Text**: `#333` - Primary text color, `#555` - Secondary text, `#666` - Tertiary text

### Header Design
- **Gradient Background**: Linear gradient from `#6aa469` (green) to `#175b98` (blue)
- **Text Color**: White on all headers
- **Padding**: 40px top/bottom, 20px left/right
- **Font Size**: 28px, bold (font-weight: 600)
- **Icon**: Emoji icon relevant to the email type

### Typography
- **Font Family**: System fonts (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, etc.)
- **Line Height**: 1.6 for body text, 1.8 for message content
- **Greeting**: 16px, margin-bottom 20px

### Common Elements

#### Info Box
```css
background-color: #f4f7fa;
border-left: 4px solid #6aa469;  /* or #175b98 for warnings */
padding: 20px;
margin: 25px 0;
border-radius: 4px;
```

#### Call-to-Action Button
```css
background-color: #6aa469;
color: white;
padding: 14px 32px;
border-radius: 6px;
font-weight: 600;
font-size: 15px;
```
Hover state: `#5a944d`

#### Warning/Alert Box
```css
background-color: #fff3cd;
border-left: 4px solid #ffc107;
padding: 15px 20px;
margin: 20px 0;
border-radius: 4px;
color: #856404;
font-size: 14px;
```

#### Footer
- **Background**: `#f4f7fa`
- **Padding**: 25px 20px
- **Text Color**: `#666`
- **Company Name**: Bold "Tūhura"
- **Links**: Company website (tuhura.co.nz) and support email
- **Copyright**: © 2025 Tūhura Tech. All rights reserved.

## Email Templates

### 1. magic_link.html / magic_link.txt
Magic link authentication for caregiver login.
- **Icon**: 🔐
- **Primary Action**: Sign In button linking to consume endpoint
- **Warning**: Link expiration time

### 2. signup_confirmation_confirmed.html / signup_confirmation_confirmed.txt
Confirmation when a student is signed up for a session.
- **Icon**: ✓
- **Content**: Session details (name, location, address, date/time)
- **Info Box**: Session details summary
- **Primary Action**: "View Your Signups" button

### 3. signup_confirmation_waitlisted.html / signup_confirmation_waitlisted.txt
Notification when a student is waitlisted.
- **Icon**: ⏳
- **Content**: Waitlist explanation, session details
- **Info Box**: Session details with blue border
- **Warning**: Why they're on waitlist

### 4. waitlist_promoted.html / waitlist_promoted.txt
Celebration when a waitlisted student gets promoted to confirmed.
- **Icon**: 🎉
- **Content**: Promotion message with session details
- **Success Notice**: Green background highlighting the promotion
- **Primary Action**: "View Your Signups" button

### 5. occurrence_cancelled.html / occurrence_cancelled.txt
Notification when a session occurrence is cancelled.
- **Icon**: ✗
- **Content**: Cancellation details and what happens next
- **Info Box**: Cancelled session details with red border
- **Notice**: Next steps and refund info

### 6. session_reminder.html / session_reminder.txt
Reminder before an upcoming session.
- **Icon**: 📅
- **Content**: Session date/time countdown, location, preparation checklist
- **Countdown**: Prominent countdown display
- **Checklist**: What to prepare before the session
- **Primary Action**: "View Full Details" button

### 7. caregiver_message.html / caregiver_message.txt
General message from Tūhura to caregivers.
- **Icon**: 💬
- **Content**: Custom message body
- **Flexible**: Used for announcements, notifications, and updates

## Template Variables

Common variables across all templates:
- `{{ caregiver_name }}` - Caregiver's name
- `{{ student_name }}` - Student's name
- `{{ session_name }}` - Session title
- `{{ support_email }}` - Support contact email
- `{{ session_venue }}` - Session location/venue (conditional)
- `{{ session_address }}` - Full address (conditional)

Authentication templates:
- `{{ magic_link_url }}` - Full consume URL
- `{{ expires_minutes }}` - Minutes until link expires

Message templates:
- `{{ subject }}` - Email subject line
- `{{ message }}` - Custom message body
- `{{ portal_url }}` - Link to caregiver portal

Session reminders:
- `{{ occurrence_date }}` - Session date
- `{{ occurrence_time }}` - Session time
- `{{ cancelled_date }}` - Date session was cancelled

## Best Practices

1. **Always include footer**: All emails must have the consistent footer with Tūhura branding
2. **Use gradient header**: All emails should use the gradient header with appropriate icon
3. **Responsive design**: All templates use max-width: 600px for mobile compatibility
4. **Plain text versions**: Always provide .txt version for email clients that don't support HTML
5. **Color consistency**: Use only colors from the palette above
6. **Clear hierarchy**: Use heading sizes (h1, h3) and spacing to create visual hierarchy
7. **Accessibility**: Use semantic HTML, proper contrast ratios, and include alt text for icons

## Testing

To test email rendering:
1. Use Mailgun's email preview feature
2. Test across major email clients: Gmail, Outlook, Apple Mail
3. Test on mobile devices (iPhone, Android)
4. Verify all links work and button styling is correct
5. Check that plain text version is readable

## Future Improvements

- Add Tūhura logo image to headers (once logo design is finalized)
- Add social media links to footer
- Consider adding tracking pixels for email engagement metrics
- Implement dark mode CSS for supported email clients
