#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const command = args[0];

const commands = {
  status: handleStatus,
  init: handleInit,
  "outline-chapters": handleOutlineChapters,
  "active-topic": handleActiveTopic,
  help: handleHelp,
};

if (!command || !commands[command]) {
  handleHelp();
  process.exit(command ? 1 : 0);
}

commands[command](args.slice(1));

function handleHelp() {
  console.log(`sws-tools — StudyWS CLI helper

Usage:
  sws-tools status [topic-dir]       Check pipeline progress for a topic
  sws-tools init <topic-slug>        Create output directory structure for a topic
  sws-tools outline-chapters <dir>   List chapter slugs from outline.json
  sws-tools active-topic             Find the most recent topic directory
  sws-tools help                     Show this help
`);
}

function handleInit(args) {
  const slug = args[0];
  if (!slug) {
    console.error("Usage: sws-tools init <topic-slug>");
    process.exit(1);
  }

  const topicDir = path.join(process.cwd(), "output", slug);
  const dirs = ["research", "chapters", "guides"];

  for (const dir of dirs) {
    fs.mkdirSync(path.join(topicDir, dir), { recursive: true });
  }

  console.log(JSON.stringify({ created: true, path: topicDir }, null, 2));
}

function handleStatus(args) {
  const outputDir = path.join(process.cwd(), "output");

  if (!fs.existsSync(outputDir)) {
    console.log(JSON.stringify({ topics: [], message: "No output directory found" }));
    return;
  }

  const topics = fs.readdirSync(outputDir).filter((f) => {
    return fs.statSync(path.join(outputDir, f)).isDirectory();
  });

  if (topics.length === 0) {
    console.log(JSON.stringify({ topics: [], message: "No topics found" }));
    return;
  }

  // If a specific topic dir was passed, filter to that
  const targetSlug = args[0];
  const toCheck = targetSlug ? topics.filter((t) => t === targetSlug) : topics;

  const results = toCheck.map((slug) => {
    const dir = path.join(outputDir, slug);
    return {
      slug,
      stages: {
        config: fs.existsSync(path.join(dir, "config.json")),
        outline: fs.existsSync(path.join(dir, "outline.json")),
        research: countFiles(path.join(dir, "research"), ".md"),
        chapters: countFiles(path.join(dir, "chapters"), ".md"),
        textbook: fs.existsSync(path.join(dir, "textbook.md")),
        guides: countFiles(path.join(dir, "guides"), ".html"),
        slides: fs.existsSync(path.join(dir, "slides.md")),
        podcast: fs.existsSync(path.join(dir, "podcast-prompt.md")),
        review: fs.existsSync(path.join(dir, "review-report.md")),
      },
    };
  });

  console.log(JSON.stringify({ topics: results }, null, 2));
}

function handleOutlineChapters(args) {
  const dir = args[0] || findActiveTopicDir();
  if (!dir) {
    console.error("Usage: sws-tools outline-chapters <topic-dir>");
    console.error("Or run from a directory with output/{slug}/outline.json");
    process.exit(1);
  }

  const outlinePath = path.join(dir, "outline.json");
  if (!fs.existsSync(outlinePath)) {
    console.error(`No outline.json found at ${outlinePath}`);
    process.exit(1);
  }

  const outline = JSON.parse(fs.readFileSync(outlinePath, "utf-8"));
  const chapters = outline.chapters.map((ch) => ({
    number: ch.number,
    slug: ch.slug,
    title: ch.title,
    sections: ch.sections.length,
    queries: (ch.research_queries || []).length,
  }));

  console.log(JSON.stringify({ chapters }, null, 2));
}

function handleActiveTopic() {
  const dir = findActiveTopicDir();
  if (!dir) {
    console.log(JSON.stringify({ found: false, message: "No topics found. Run /sws:start" }));
    return;
  }

  const slug = path.basename(dir);
  const configPath = path.join(dir, "config.json");
  let config = null;
  if (fs.existsSync(configPath)) {
    config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
  }

  console.log(JSON.stringify({
    found: true,
    slug,
    path: dir,
    topic: config?.topic || slug,
    pipeline_stage: config?.pipeline_stage || "unknown",
  }, null, 2));
}

function countFiles(dir, ext) {
  if (!fs.existsSync(dir)) return 0;
  return fs.readdirSync(dir).filter((f) => f.endsWith(ext)).length;
}

function findActiveTopicDir() {
  const outputDir = path.join(process.cwd(), "output");
  if (!fs.existsSync(outputDir)) return null;

  const topics = fs.readdirSync(outputDir).filter((f) =>
    fs.statSync(path.join(outputDir, f)).isDirectory()
  );

  // Return the most recently modified topic dir
  if (topics.length === 0) return null;

  const sorted = topics
    .map((t) => ({
      name: t,
      mtime: fs.statSync(path.join(outputDir, t)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);

  return path.join(outputDir, sorted[0].name);
}
