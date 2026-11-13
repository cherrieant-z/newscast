# -*- coding: utf-8 -*-
"""小红书分享链接 → 正文。投喂口的前置工具。

为什么需要它：小红书首页对服务器 IP 是登录墙，搜索接口要签名，
但它「被分享出来的那一条」是开放的——短链跳转后的详情页，
正文完整地写在 og:description 里，不需要登录态。

2026-11-13 实测：移动端 UA 拿 `xhslink.cn/o/xxxx`，
跟到详情页后 head 里就有 og:title 和 og:description，一千三百多字全在。
换成桌面端 UA 会掉到登录页，所以 UA 必须装成手机。

边界也要写清楚：这只对「已经拿到的那条链接」有效。
自动发现新笔记（搜索、推荐流）仍然要登录态，那条路走不通，别在这上面耗。

用法：
    python tools/xhs_shot.py https://xhslink.cn/o/5vakhCrbAMd
    python tools/xhs_shot.py <链接> -o cases/inbox/2026-11-13-01.txt
"""
import argparse
import html as H
import re
import sys

import httpx

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
             "Mobile/15E148 Safari/604.1")


def _meta(page: str, prop: str) -> str:
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"'
                  % re.escape(prop), page)
    if not m:
        m = re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"'
                      % re.escape(prop), page)
    return H.unescape(m.group(1)) if m else ""


def _tidy(text: str) -> str:
    """把笔记正文整理成能读的段落。

    小红书正文里的段落分隔不是换行，是一串空格加制表符（富文本编辑器留下的），
    直接按原样存进来，整篇会挤成一大段，后面按句读切段会切得乱七八糟。
    制表符在正文里只当分隔用，所以先拿它断段，再把剩下的连续空格压成一个。
    """
    text = re.sub(r"[ \u3000]*\t[ \t\u3000]*", "\n", text)
    text = re.sub(r"[ \u3000]{2,}", " ", text)
    # 话题标签对播报没用，去掉
    text = re.sub(r"#[^#\s]{1,20}(\s|$)", "", text)
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    return "\n\n".join(paras)


def fetch(url: str, timeout: float = 25.0) -> dict:
    with httpx.Client(headers={"User-Agent": MOBILE_UA},
                      follow_redirects=True, timeout=timeout) as c:
        r = c.get(url)
        page = r.text
        final = str(r.url)

    title = _meta(page, "og:title") or _meta(page, "title")
    desc = _meta(page, "og:description") or _meta(page, "description")
    if not desc:
        raise RuntimeError(
            "页面里没有正文。多半是链接过期了，或者这条是纯图片笔记——"
            "重新去 App 里点一次「分享 → 复制链接」再试。")

    title = re.sub(r"\s*-\s*小红书$", "", title).strip()
    # 详情页的 query 里全是追踪参数，去重只认笔记 id
    m = re.search(r"/(?:discovery/item|explore)/([0-9a-f]{24})", final)
    clean_url = (f"https://www.xiaohongshu.com/explore/{m.group(1)}"
                 if m else final.split("?")[0])

    return {"title": title, "body": _tidy(desc), "url": clean_url}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-o", "--out", help="写到投喂目录，不加就打到终端")
    args = ap.parse_args()

    try:
        shot = fetch(args.url)
    except Exception as e:
        print(f"抓取失败：{e}", file=sys.stderr)
        return 1

    text = f"{shot['title']}\n链接：{shot['url']}\n\n{shot['body']}\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"已写入 {args.out}（正文 {len(shot['body'])} 字）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
