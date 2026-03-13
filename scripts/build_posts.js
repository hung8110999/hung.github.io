const fs = require('fs');
const path = require('path');

const markdownPostsDir = path.join(__dirname, '../markdown_posts');
const outputPostsDir = path.join(__dirname, '../posts');
const assetsImagesDir = path.join(__dirname, '../assets/images/posts');

// Ensure image directory exists
if (!fs.existsSync(assetsImagesDir)) {
    fs.mkdirSync(assetsImagesDir, { recursive: true });
}

const templateFile = path.join(__dirname, 'post_template.html');
const templateContent = fs.readFileSync(templateFile, 'utf8');

// Basic Markdown to HTML converter (regex-based)
function convertMarkdownToHtml(markdown, folderName) {
    let html = markdown;

    // Headings
    html = html.replace(/^# (.*$)/gm, '<h1 style="font-size: var(--fs-4xl); margin-bottom: var(--space-lg); line-height: 1.2;">$1</h1>');
    html = html.replace(/^## (.*$)/gm, '<h2 style="margin-top: var(--space-2xl); margin-bottom: var(--space-md); font-size: var(--fs-2xl);">$1</h2>');
    html = html.replace(/^### (.*$)/gm, '<h3 style="margin-top: var(--space-xl); margin-bottom: var(--space-sm); font-size: var(--fs-xl);">$1</h3>');

    // Bold & Italic
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Images: ![alt](path){style}
    // We reference images directly from markdown_posts folder
    // Added support for optional {style} after image
    html = html.replace(/!\[(.*?)\]\((.*?)\)(?:{(.*?)})?/g, (match, alt, imgPath, style) => {
        // Normalize path and ensure it's relative to the posts/ folder
        const normalizedImgPath = imgPath.replace(/\\/g, '/');
        const finalImgPath = `../markdown_posts/${folderName}/${normalizedImgPath}`;
        
        let inlineStyle = 'width: 100%; border-radius: var(--radius-lg); margin-top: var(--space-xl); border: 1px solid var(--border-light);';
        if (style) {
            inlineStyle = style; // Use user defined style if provided
        }
        
        return `<img src="${finalImgPath}" alt="${alt}" style="${inlineStyle}">`;
    });

    // Lists
    html = html.replace(/^\- (.*$)/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gms, '<ul style="margin-bottom: var(--space-lg);">$1</ul>');

    // Paragraphs (naive: anything not starting with <)
    const lines = html.split('\n');
    const processedLines = lines.map(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('<') && !trimmed.startsWith('<!--')) {
            return `<p style="margin-bottom: var(--space-lg);">${trimmed}</p>`;
        }
        return line;
    });
    html = processedLines.join('\n');

    return html;
}

function generatePost(folderName) {
    const postDir = path.join(markdownPostsDir, folderName);
    const markdownFile = path.join(postDir, 'blog.md');

    if (!fs.existsSync(markdownFile)) return;

    const content = fs.readFileSync(markdownFile, 'utf8');

    // Extract metadata
    const dateMatch = content.match(/date:\s*(.*)/);
    const descMatch = content.match(/description:\s*(.*)/);
    const date = dateMatch ? dateMatch[1].trim() : '2026-03-01';
    const description = descMatch ? descMatch[1].trim() : 'No description available.';

    // Extract Title (first H1)
    const titleMatch = content.match(/^# (.*$)/m);
    const title = titleMatch ? titleMatch[1].trim() : folderName;

    // Clean markdown for conversion (remove metadata comments)
    const markdownBody = content.replace(/<!--[\s\S]*?-->/, '').trim();
    const bodyHtml = convertMarkdownToHtml(markdownBody, folderName);

    // Prepare HTML from template
    let finalHtml = templateContent;

    const d = new Date(date);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    const formattedDate = d.toLocaleDateString('en-US', options);

    const cleanBodyHtml = bodyHtml.replace(/<h1.*?>.*?<\/h1>/i, '');

    // Replace Placeholders
    finalHtml = finalHtml.replace(/{{TITLE}}/g, title);
    finalHtml = finalHtml.replace(/{{DESCRIPTION}}/g, description);
    finalHtml = finalHtml.replace(/{{DATE}}/g, date);
    finalHtml = finalHtml.replace(/{{FORMATTED_DATE}}/g, formattedDate);
    finalHtml = finalHtml.replace(/{{CONTENT}}/g, cleanBodyHtml);

    const outputPath = path.join(outputPostsDir, `${folderName}.html`);
    fs.writeFileSync(outputPath, finalHtml);
    console.log(`Generated: ${outputPath}`);
}

// Run for all folders in markdown_posts
fs.readdirSync(markdownPostsDir).forEach(file => {
    const fullPath = path.join(markdownPostsDir, file);
    if (fs.statSync(fullPath).isDirectory()) {
        generatePost(file);
    }
});
