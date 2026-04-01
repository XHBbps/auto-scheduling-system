const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const appRoot = path.resolve(__dirname, '..');
const assetsDir = path.resolve(appRoot, 'dist', 'assets');
const outputPath = path.resolve(appRoot, '..', '..', 'docs', '前端-chunk-观测.md');

if (!fs.existsSync(assetsDir)) {
  throw new Error(`dist assets not found: ${assetsDir}`);
}

const formatKiB = (bytes) => `${(bytes / 1024).toFixed(2)} KB`;

const files = fs.readdirSync(assetsDir)
  .map((name) => {
    const fullPath = path.join(assetsDir, name);
    const stat = fs.statSync(fullPath);
    const content = fs.readFileSync(fullPath);
    const gzipSize = zlib.gzipSync(content).length;
    const ext = path.extname(name).slice(1) || 'other';
    const kind = name.includes('vendor') ? 'vendor' : name.includes('Page-') ? 'page' : 'shared';
    return {
      name,
      ext,
      kind,
      size: stat.size,
      gzipSize,
    };
  })
  .sort((a, b) => b.size - a.size);

const topOverall = files.slice(0, 15);
const topJs = files.filter((item) => item.ext === 'js').slice(0, 12);
const topCss = files.filter((item) => item.ext === 'css').slice(0, 8);
const pageChunks = files.filter((item) => item.kind === 'page' && item.ext === 'js').slice(0, 10);
const vendorChunks = files.filter((item) => item.kind === 'vendor' && item.ext === 'js').slice(0, 10);

const totalJs = files.filter((item) => item.ext === 'js').reduce((sum, item) => sum + item.size, 0);
const totalCss = files.filter((item) => item.ext === 'css').reduce((sum, item) => sum + item.size, 0);
const largestJs = topJs[0];
const largestCss = topCss[0];

const table = (rows) => {
  const header = ['| 文件 | 类型 | 原始大小 | gzip |', '|---|---:|---:|---:|'].join('\n');
  const body = rows
    .map((item) => `| ${item.name} | ${item.ext.toUpperCase()} | ${formatKiB(item.size)} | ${formatKiB(item.gzipSize)} |`)
    .join('\n');
  return `${header}\n${body}`;
};

const lines = [
  '# 前端 chunk 观测',
  '',
  `- 生成时间：${new Date().toISOString()}`,
  `- 统计目录：\`apps/web/dist/assets\``,
  `- JS 总体积：${formatKiB(totalJs)}`,
  `- CSS 总体积：${formatKiB(totalCss)}`,
  largestJs ? `- 最大 JS chunk：\`${largestJs.name}\`（${formatKiB(largestJs.size)}）` : '- 最大 JS chunk：无',
  largestCss ? `- 最大 CSS chunk：\`${largestCss.name}\`（${formatKiB(largestCss.size)}）` : '- 最大 CSS chunk：无',
  '',
  '## Top Overall',
  '',
  table(topOverall),
  '',
  '## Top JS',
  '',
  table(topJs),
  '',
  '## Top CSS',
  '',
  table(topCss),
  '',
  '## Page Chunks',
  '',
  table(pageChunks),
  '',
  '## Vendor Chunks',
  '',
  table(vendorChunks),
  '',
  '## 当前观察结论',
  '',
  '- 图表依赖仍主要集中在 `charts-components-vendor` 与 `charts-series-vendor`。',
  '- 日期与表格能力仍主要集中在 `element-plus-date-vendor` 与 `element-plus-table-vendor`。',
  '- 当前页面主 chunk 中，`UserManagementPage`、`SyncConsolePage`、`MachineScheduleListPage`、`PartScheduleListPage` 仍是相对较大的业务页面块，后续适合持续观察其拆分收益。',
  '- 后续每次涉及图表、日期组件、列表页大重构时，建议执行 `npm run build:observe` 并对比本文件。',
  '',
];

fs.writeFileSync(outputPath, lines.join('\n'), 'utf8');
console.log(`Chunk report written to ${outputPath}`);
