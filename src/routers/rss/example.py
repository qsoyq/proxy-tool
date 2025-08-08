import logging
from fastapi import APIRouter, Request
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem


router = APIRouter(tags=["RSS"], prefix="/rss")

logger = logging.getLogger(__file__)

content_html = """
<div id="expanded" class="style-scope ytd-text-inline-expander"><yt-attributed-string user-input="" class="style-scope ytd-text-inline-expander"><span class="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap" dir="auto"><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">THE FIRST TAKE is a YouTube Channel dedicated to filming musicians and singers performing in a single take.

Episode 552 welcomes the six-member group IVE, consisting of YUJIN, GAEUL, REI, WONYOUNG, LIZ, and LEESEO, making their first appearance on THE FIRST TAKE.
Having swept numerous rookie awards at various music ceremonies, they will perform "After LIKE," which has ranked number one on all major Korean music charts.
This song has also charted on the U.S. Billboard Global 200 for 17 weeks, demonstrating its high popularity not only in Korea but worldwide.
Enjoy a special one-take performance exclusively for THE FIRST TAKE.

STREAMING &amp; DOWNLOAD：</span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbmNYUmNFTUMta0tpaU1xZGNBcGIzV3hkOEhDQXxBQ3Jtc0tuNWVEUndpRzAwUHZ1ZHlCVnNiWXBnOW9aNlRXSE5VanNocW1VOVpzOURRblR3bm9RZkpoUnFXN2dJR3A5R2NDaXZ3SEJ1a3pmM3REdzIxakF5ZWwzWnVoUUhzSnFnVEpFT09QSjlkVmg5MEdfcnhjYw&amp;q=https%3A%2F%2Flnk.to%2FQJgcyzJX&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">https://lnk.to/QJgcyzJX</a></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">


■IVE OFFICIAL
YouTube: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"><span style="background-color: rgba(0,0,0,0.051); border-radius: 8px; padding-bottom: 1px;" class="yt-core-attributed-string--highlight-text-decorator" dir="auto"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" aria-label="YouTube Channel Link: IVEstarship" href="https://www.youtube.com/c/IVEstarship" rel="nofollow" target="" force-new-state="true">&nbsp;&nbsp;<span class="yt-core-attributed-string--inline-block-mod" style="margin-top: 0.5px;"><img alt="" class="yt-core-image yt-core-attributed-string__image-element yt-core-attributed-string__image-element--image-alignment-vertical-center yt-core-image--content-mode-scale-to-fill yt-core-image--loaded" style="height: 10px; width: 14px;" src="https://www.gstatic.com/youtube/img/watch/yt_favicon_ringo2.png"></span>&nbsp;/&nbsp;ivestarship&nbsp;&nbsp;</a></span></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
X: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbHFub2lDUDY0dk45SGRDQnRQLWFNalJoNGthZ3xBQ3Jtc0tuTURMcXVFdktORU5SOTQ1b3lvanB6T2w4NGlsZTQ5dXllM2tKTTdhZzY0LUY0QzVqeHVqTmV0T2NnSW5paDRMYWtQZG5JT25KRjIyLVJUNmtXdzdweVViZ2x5M1hPLTZqZUlvbERBODNZbE0zWTVHaw&amp;q=https%3A%2F%2Fx.com%2FIVEstarship&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">https://x.com/IVEstarship</a></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
Instagram: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"><span style="background-color: rgba(0,0,0,0.051); border-radius: 8px; padding-bottom: 1px;" class="yt-core-attributed-string--highlight-text-decorator" dir="auto"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" aria-label="Instagram Channel Link: IVEstarship" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbGdVdW5DQzZwcXhrY1MxZmpiUnNZcFE1clVaZ3xBQ3Jtc0tseGNGUjRNZjgwMjZMNjBCWm0xczMyck1DeTRIZGExcFRHbTlxNHpCd1VCSFo0MkkwZmpJNDhvTEhnNldpeUR3VldBbi0zbmxnLXRBS3ZfWHBmRnRDOEZzaGowVmxVTjVnVUU0OXRDV09oRHA4ek9pSQ&amp;q=https%3A%2F%2Fwww.instagram.com%2FIVEstarship%2F&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">&nbsp;<span class="yt-core-attributed-string--inline-block-mod" style="margin-top: 0.5px;"><img alt="" class="yt-core-image yt-core-attributed-string__image-element yt-core-attributed-string__image-element--image-alignment-vertical-center yt-core-image--content-mode-scale-to-fill yt-core-image--loaded" style="height: 14px; width: 14px;" src="https://www.gstatic.com/youtube/img/watch/social_media/instagram_1x.png"></span>&nbsp;/&nbsp;ivestarship&nbsp;&nbsp;</a></span></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
TikTok: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"><span style="background-color: rgba(0,0,0,0.051); border-radius: 8px; padding-bottom: 1px;" class="yt-core-attributed-string--highlight-text-decorator" dir="auto"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" aria-label="TikTok Channel Link: ive.official" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbkM2elpiVmZMS25IVXE2WXlpUGtMU2hLMnRWZ3xBQ3Jtc0tsY01mcEg5M1JTOVlRVDBGMS00SVgwZXBKNENuM3YzOWhjSVlub2E5SE1IVElsV3dhMzI3SE42TTZXTEh2QWdLZnhJclo0eWdOTXp4TzFPM2FGei0xckQzTFFBaENNbUhVWDBnbktvdDJIMmNfV3BGaw&amp;q=https%3A%2F%2Fwww.tiktok.com%2F%40ive.official&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">&nbsp;<span class="yt-core-attributed-string--inline-block-mod" style="margin-top: 0.5px;"><img alt="" class="yt-core-image yt-core-attributed-string__image-element yt-core-attributed-string__image-element--image-alignment-vertical-center yt-core-image--content-mode-scale-to-fill yt-core-image--loaded" style="height: 14px; width: 14px;" src="https://www.gstatic.com/youtube/img/watch/social_media/tiktok_1x.png"></span>&nbsp;/&nbsp;ive.official&nbsp;&nbsp;</a></span></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">

■「THE FIRST TAKE」OFFICIAL
Web Site: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbEZqOXAwSEt3dzNsaUF2VndRbVFwQ3g0U1VGd3xBQ3Jtc0ttMXZvUXVFQngxaDdScUxoNmVhNHpMdkdvQTFZWVpTcHhVWlF2MlRSRGVHVUFXRm1FT0dSVVgyWHBaRXZiOEMtendSRnl3cVdNb3NwdENXendqUy1PdnlqOXFjZXRaWnZEUFZfWUl6b01xVGJIcjNDMA&amp;q=https%3A%2F%2Fwww.thefirsttake.jp%2F&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">https://www.thefirsttake.jp/</a></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
Instagram: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"><span style="background-color: rgba(0,0,0,0.051); border-radius: 8px; padding-bottom: 1px;" class="yt-core-attributed-string--highlight-text-decorator" dir="auto"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" aria-label="Instagram Channel Link: the_firsttake" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbmpBTXlQZDZrTUNYc2E5LXBYb3RCeFBQd2VOUXxBQ3Jtc0ttWTBrcnVvcHJpX3QtX2lSU0NQdXlVR250WEp6b1VOMTlEa1MwelFzMUlFNzVoTWlpcUlHMWliT0MwdnVOQ1oxWTZETUdwS1dOdmMtb2NFUlJGb3p3SXpTX0F1TmxTTk9objJNd0lHcWczSk5YTUV6OA&amp;q=https%3A%2F%2Fwww.instagram.com%2Fthe_firsttake%2F&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">&nbsp;<span class="yt-core-attributed-string--inline-block-mod" style="margin-top: 0.5px;"><img alt="" class="yt-core-image yt-core-attributed-string__image-element yt-core-attributed-string__image-element--image-alignment-vertical-center yt-core-image--content-mode-scale-to-fill yt-core-image--loaded" style="height: 14px; width: 14px;" src="https://www.gstatic.com/youtube/img/watch/social_media/instagram_1x.png"></span>&nbsp;/&nbsp;the_firsttake&nbsp;&nbsp;</a></span></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
X: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"><span style="background-color: rgba(0,0,0,0.051); border-radius: 8px; padding-bottom: 1px;" class="yt-core-attributed-string--highlight-text-decorator" dir="auto"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" aria-label="Twitter Channel Link: The_FirstTake" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbkpEMmhnTmlkR1JBMHROSHVjTnFmNTFUUVg3d3xBQ3Jtc0ttSjEtS183RmJwTVRrd2NBczYzUGMtNkJ1ck1zLUlfZ3hQZ3BtU1ZaWTQ0SVBUOVRleUFiLTVTdktBRnpBbkRfOEVJQzdZVzdXdGM5dmhISkJRRjZURW9tX3gtTEowaUhQYnNIUlNrSk9YZzhRYTB5VQ&amp;q=https%3A%2F%2Ftwitter.com%2FThe_FirstTake&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">&nbsp;<span class="yt-core-attributed-string--inline-block-mod" style="margin-top: 0.5px;"><img alt="" class="yt-core-image yt-core-attributed-string__image-element yt-core-attributed-string__image-element--image-alignment-vertical-center yt-core-image--content-mode-scale-to-fill yt-core-image--loaded" style="height: 14px; width: 14px;" src="https://www.gstatic.com/youtube/img/watch/social_media/twitter_1x_v2.png"></span>&nbsp;/&nbsp;the_firsttake&nbsp;&nbsp;</a></span></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
TikTok: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"><span style="background-color: rgba(0,0,0,0.051); border-radius: 8px; padding-bottom: 1px;" class="yt-core-attributed-string--highlight-text-decorator" dir="auto"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" aria-label="TikTok Channel Link: the_first_take" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbGcycnJ4aHBaV0dpYzBBa0EzcmhQSzZ2MW9xZ3xBQ3Jtc0ttaXdJaWJkdktSRFRrdEV1c01peWxKWVNFclJJT1E3T2w5anJQOUYzcEZpVW9KdDMyZjlXbk4zVFo4TV9aVEVBUDdtQWd5dk5sQnYxNVpBZUs1YXBmOVpuSDFBT2ZpMXI4Y0JQUFlyYWVwT3RBMUtIUQ&amp;q=https%3A%2F%2Fwww.tiktok.com%2F%40the_first_take&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">&nbsp;<span class="yt-core-attributed-string--inline-block-mod" style="margin-top: 0.5px;"><img alt="" class="yt-core-image yt-core-attributed-string__image-element yt-core-attributed-string__image-element--image-alignment-vertical-center yt-core-image--content-mode-scale-to-fill yt-core-image--loaded" style="height: 14px; width: 14px;" src="https://www.gstatic.com/youtube/img/watch/social_media/tiktok_1x.png"></span>&nbsp;/&nbsp;the_first_take&nbsp;&nbsp;</a></span></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">
THE FIRST TIMES: </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="https://www.youtube.com/redirect?event=video_description&amp;redir_token=QUFFLUhqbUNIM0xIcGlpdzdSMFpSOUxqcnRjU25TZVVNZ3xBQ3Jtc0trQWJ5ZE5tbUNIZm5lYUFiUmVNd2ZUYXd0V3VZNzdzT2ZlVjFDLWI4UFV3R2hqRjRnenhlTHZIVkF1aUJpZWk0NUNGUDBHQWxUb2p3ODNPeDJpUkJCTEZvVHBsNFRGdEszdUZqbXRndlRCeVU5LVg5bw&amp;q=https%3A%2F%2Fwww.thefirsttimes.jp%2F&amp;v=BiTEQGmPRfQ" rel="nofollow" target="_blank" force-new-state="true">https://www.thefirsttimes.jp/</a></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);">

■THE FIRST TAKE Rules
A microphone and a white studio.

And 1 rule.
You’ve got 1 TAKE.

■THE FIRST TAKE Concept
CAPTURE THE TAKE.
THIS MOMENT.
THIS SOUND.

THE FIRST TAKE
IT ONLY HAPPENS ONCE.


CREDITS
―
Director/Creative Director: Keisuke Shimizu
Art Director: Yo Kimura
Copywriter: Hiroshi Yamazaki
Director of Photography: Kazuki Nagayama
DIT: Toru Miura (Spice)
Camera Assistant: Yuri Koichi, Kazuhisa Sakamoto, YutoYamada (Spice)
Lighting Director: Naoya Imaoka
Chief Lighting Assistant: Yukinori Suda
Lighting Assistant: Hagihara Kouta, Hidetaka Sato, Chihiro Homan, Ren Jialin
Stage Carpenter: studio noll
Offline Editor: Masato Kudo (FAB)
Colorist/Online Editor: Junya Akahoshi
Production Assistant: Kai Takaha, Kazuki Hirayama, Yasuhiro Koshida, Kaoru Shirasuna
Producer: Masato Kudo (FAB)
Stylist: KANG DA YOUNG, JANG JINKYOUNG
Make up: YE MIJIN, DAYOON
Hair: BODA, HARIN

</span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="/hashtag/thefirsttake" target="" force-new-state="true">#THEFIRSTTAKE</a></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"> </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="/hashtag/ive" target="" force-new-state="true">#IVE</a></span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(19, 19, 19);"> </span><span class="yt-core-attributed-string--link-inherit-color" dir="auto" style="color: rgb(6, 95, 212);"><a class="yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color" tabindex="0" href="/hashtag/afterlike" target="" force-new-state="true">#Afterlike</a></span></span></yt-attributed-string><yt-formatted-string disable-attributed-string="" class="style-scope ytd-text-inline-expander" is-empty="" hidden="" disable-upgrade=""></yt-formatted-string></div>
"""


@router.get("/jsonfeed/example", response_model=JSONFeed, summary="JSONFeed 示例")
async def jsonfeed(
    req: Request,
):
    """jsonfeed example"""

    host = req.url.hostname
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "YouTube",
        "description": "YouTube",
        "home_page_url": "https://www.youtube.com",
        "feed_url": f"{req.url.scheme}://{host}/api/rss/jsonfeed",
        "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/YouTube.png",
        "favicon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/YouTube.png",
        "items": items,
    }

    payload = {
        "author": {
            "url": "https://www.youtube.com/@The_FirstTake",
            "name": "The_FirstTake",
            "avatar": "https://yt3.googleusercontent.com/HqKlAwVvfGeRo6NJ7wZHoE20Ov6640WHw17sF8mhJe6bPNp0e78-3c546VevqnjAbAY6w9Sw=s160-c-k-c0x00ffffff-no-rj",
        },
        "url": "https://www.youtube.com/watch?v=BiTEQGmPRfQ",
        "title": "IVE - After LIKE / THE FIRST TAKE",
        "id": "BiTEQGmPRfQ",
        "date_published": "2025-08-08 06:00:00 CST",
        "content_html": content_html,
    }
    items.append(JSONFeedItem(**payload))
    return feed
