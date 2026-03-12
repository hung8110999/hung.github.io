const fs = require('fs');
const path = require('path');

const postsDir = path.join(__dirname, '../posts');
const outputFile = path.join(__dirname, '../posts.json');

const getPosts = () => {
    let posts = [];
    const files = fs.readdirSync(postsDir);

    files.forEach(file => {
        if (file.endsWith('.html')) {
            const filePath = path.join(postsDir, file);
            const content = fs.readFileSync(filePath, 'utf8');

            const titleMatch = content.match(/<title>(.*?)(?: —.*)?<\/title>/i);
            const dateMatch = content.match(/<meta\s+name=["']date["']\s+content=["'](.*?)["']/i);
            let descMatch = content.match(/<meta\s+name=["']description["']\s+content=["'](.*?)["']/i);

            // In some cases description could be split across lines, handling that with basic regex
            if (!descMatch) {
                descMatch = content.match(/<meta\s+name=["']description["'][\s\S]*?content=["']([\s\S]*?)["']/i);
            }

            if (titleMatch && dateMatch) {
                let description = descMatch ? descMatch[1].replace(/\s+/g, ' ').trim() : "No description available.";
                let title = titleMatch[1].trim();
                let dateStr = dateMatch[1].trim();

                posts.push({
                    title: title,
                    date: dateStr,
                    description: description,
                    url: `posts/${file}`
                });
            } else {
                console.warn(`Missing title or date in ${file}`);
            }
        }
    });

    // Sort posts from newest to oldest
    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    return posts;
};

const posts = getPosts();
fs.writeFileSync(outputFile, JSON.stringify(posts, null, 2));
console.log(`Generated posts.json with ${posts.length} posts.`);
