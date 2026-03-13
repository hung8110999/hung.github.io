const fs = require('fs');
const path = require('path');

const markdownPostsDir = path.join(__dirname, '../markdown_posts');
const outputPostsDir = path.join(__dirname, '../posts');
const assetsImagesDir = path.join(__dirname, '../assets/images/posts');

// Ensure image directory exists
if (!fs.existsSync(assetsImagesDir)) {
    fs.mkdirSync(assetsImagesDir, { recursive: true });
}

const templateFile = path.join(outputPostsDir, 'self-study-ai-math.html');
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

    // Images: ![alt](path)
    // We reference images directly from markdown_posts folder
    html = html.replace(/!\[(.*?)\]\((.*?)\)/g, (match, alt, imgPath) => {
        // Normalize path and ensure it's relative to the posts/ folder
        const normalizedImgPath = imgPath.replace(/\\/g, '/');
        const finalImgPath = `../markdown_posts/${folderName}/${normalizedImgPath}`;
        
        return `<img src="${finalImgPath}" alt="${alt}" style="width: 100%; border-radius: var(--radius-lg); margin-top: var(--space-xl); border: 1px solid var(--border-light);">`;
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

    // Replace Metadata
    finalHtml = finalHtml.replace(/<title>.*?<\/title>/i, `<title>${title} — Hung's Blog</title>`);
    finalHtml = finalHtml.replace(/<meta\s+name=["']description["']\s+content=["'].*?["']/i, `<meta name="description" content="${description}"`);
    finalHtml = finalHtml.replace(/<meta\s+name=["']date["']\s+content=["'].*?["']/i, `<meta name="date" content="${date}"`);

    // Replace Header Date and Title
    finalHtml = finalHtml.replace(/<div[^>]*color:\s*var\(--blue-600\)[^>]*>([\s\S]*?)<\/div>/i, (match, p1) => {
        const d = new Date(date);
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = d.toLocaleDateString('en-US', options);
        return match.replace(p1, formattedDate);
    });
    
    // Find the H1 in the main content and replace it
    // The template has the H1 for the blog post title
    finalHtml = finalHtml.replace(/<h1[^>]*>[\s\S]*?<\/h1>/i, `<h1 style="font-size: var(--fs-4xl); margin-bottom: var(--space-lg); line-height: 1.2;">${title}</h1>`);

    // Replace Content
    // In our template, the content is inside <div class="topic-content" ...>
    const contentRegex = /<div\s+class=["']topic-content["'][\s\S]*?>([\s\S]*?)<\/div>\s*<!-- Footer Call to Action -->/i;
    finalHtml = finalHtml.replace(contentRegex, (match, p1) => {
        // We remove the first h1 from bodyHtml since we already set it in the header
        const cleanBodyHtml = bodyHtml.replace(/<h1.*?>.*?<\/h1>/i, '');
        return `<div class="topic-content" style="font-size: var(--fs-lg); line-height: 1.8; color: var(--text-primary); padding: 0;">\n${cleanBodyHtml}\n</div>\n<!-- Footer Call to Action -->`;
    });

    // Remove the sample image from template if it's there
    finalHtml = finalHtml.replace(/<img\s+src=["']\.\.\/assets\/images\/sample_blog_img\.png["'][\s\S]*?>/i, '');

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
