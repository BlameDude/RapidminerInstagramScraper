import time
import requests
from requests_html import HTMLSession
import re
import json
import hashlib
import os
from slugify import slugify
import http.cookiejar
import http.cookiejar
import textwrap
import urllib.parse
import pandas as pd
from emoji import unicode_codes
import re

_DEFAULT_DELIMITER = ':'
_EMOJI_REGEXP = None

BASE_URL = 'https://www.instagram.com'
LOGIN_URL = 'https://www.instagram.com/accounts/login/ajax/'
MEDIA_LINK = 'https://www.instagram.com/p/%s'
COMMENTS_BEFORE_COMMENT_ID_BY_CODE = 'https://www.instagram.com/graphql/query/?query_hash=97b41c52301f77ce508f55e66d17620e&variables=%s'

def get_emoji_regexp(language='en'):
    global _EMOJI_REGEXP
    EMOJI_UNICODE = unicode_codes.EMOJI_UNICODE[language]
    if _EMOJI_REGEXP is None:
        emojis = sorted(EMOJI_UNICODE.values(), key=len, reverse=True)
        pattern = u'(' + u'|'.join(re.escape(u) for u in emojis) + u')'
        _EMOJI_REGEXP = re.compile(pattern)
    return _EMOJI_REGEXP

def demojize(string,language,use_aliases=False,delimiters=(_DEFAULT_DELIMITER, _DEFAULT_DELIMITER)):
    UNICODE_EMOJI = unicode_codes.UNICODE_EMOJI[language]
    def replace(match):
        codes_dict = unicode_codes.UNICODE_EMOJI_ALIAS_ENGLISH if use_aliases else UNICODE_EMOJI
        val = codes_dict.get(match.group(0), match.group(0))
        return delimiters[0] + val[1:-1] + delimiters[1]

    return re.sub(u'\ufe0f', '', (get_emoji_regexp(language).sub(replace, string)))

def get_media_page_link(code):
    return MEDIA_LINK % urllib.parse.quote_plus(code)

def get_comments_before_comments_id_by_code(variables):
    return COMMENTS_BEFORE_COMMENT_ID_BY_CODE % urllib.parse.quote_plus(json.dumps(variables, separators=(',', ':')))
      
class InstagramException(Exception):
    def __init__(self, message="", code=500):
        super().__init__(f'{message}, Code:{code}')
    
    @staticmethod
    def default(response_text, status_code):
        return InstagramException(
            'Response code is {status_code}. Body: {response_text} '
            'Something went wrong. Please report issue.'.format(
                response_text=response_text, status_code=status_code),
            status_code)

class CookieSessionManager:
    def __init__(self, session_folder, filename):
        self.session_folder = session_folder
        self.filename = filename

    def get_saved_cookies(self):
        try:
            f = open(self.session_folder + self.filename, 'r') 
            return f.read()
        except FileNotFoundError:
            return None

    def set_saved_cookies(self, cookie_string):
        if not os.path.exists(self.session_folder):
            os.makedirs(self.session_folder)

        with open(self.session_folder + self.filename,"w+") as f:
            f.write(cookie_string)

    def empty_saved_cookies(self):
        try:
            os.remove(self.session_folder + self.filename)
        except FileNotFoundError:
            pass

class InitializerModel:

    def __init__(self, props=None):

        self._is_new = True
        self._is_loaded = False
        """init data was empty"""
        self._is_load_empty = True
        self._is_fake = False
        self._modified = None

        """Array of initialization data"""
        self._data = {}

        self.modified = time.time()

        if props is not None and len(props) > 0:
            self._init(props)

    def _init(self, props):
        """

        :param props: props array
        :return: None
        """
        for key in props.keys():
            try:
                self._init_properties_custom(props[key], key, props)
            except AttributeError:
                self._data[key] = props[key]

        self._is_new = False
        self._is_loaded = True
        self._is_load_empty = False

class Account(InitializerModel):

    def __init__(self, props=None):
        self.identifier = None
        self.username = None
        self.full_name = None
        self.profile_pic_url = None
        self.profile_pic_url_hd = None
        self.biography = None
        self.external_url = None
        self.follows_count = 0
        self.followed_by_count = 0
        self.media_count = 0
        self.is_private = False
        self.is_verified = False
        self.medias = []
        self.blocked_by_viewer = False
        self.country_block = False
        self.followed_by_viewer = False
        self.follows_viewer = False
        self.has_channel = False
        self.has_blocked_viewer = False
        self.highlight_reel_count = 0
        self.has_requested_viewer = False
        self.is_business_account = False
        self.is_joined_recently = False
        self.business_category_name = None
        self.business_email = None
        self.business_phone_number = None
        self.business_address_json = None
        self.requested_by_viewer = False
        self.connected_fb_page = None

        super(Account, self).__init__(props)

    def get_profile_picture_url(self):
        try:
            if not self.profile_pic_url_hd == '':
                return self.profile_pic_url_hd
        except AttributeError:
            try:
                return self.profile_pic_url
            except AttributeError:
                return ''

    def __str__(self):
        string = f"""
        Account info:
        Id: {self.identifier}
        Username: {self.username if hasattr(self, 'username') else '-'}
        Full Name: {self.full_name if hasattr(self, 'full_name') else '-'}
        Bio: {self.biography if hasattr(self, 'biography') else '-'}
        Profile Pic Url: {self.get_profile_picture_url()}
        External url: {self.external_url if hasattr(self, 'external_url') else '-'}
        Number of published posts: {self.media_count if hasattr(self, 'media_count') else '-'}
        Number of followers: {self.followed_by_count if hasattr(self, 'followed_by_count') else '-'}
        Number of follows: {self.follows_count if hasattr(self, 'follows_count') else '-'}
        Is private: {self.is_private if hasattr(self, 'is_private') else '-'}
        Is verified: {self.is_verified if hasattr(self, 'is_verified') else '-'}
        """
        return textwrap.dedent(string)

    """
     * @param Media $media
     * @return Account
    """
    def add_media(self, media):
        try:
            self.medias.append(media)
        except AttributeError:
            raise AttributeError

    def _init_properties_custom(self, value, prop, array):
        
        if prop == 'id':
            self.identifier = value

        standart_properties = [
            'username',
            'full_name',
            'profile_pic_url',
            'profile_pic_url_hd',
            'biography',
            'external_url',
            'is_private',
            'is_verified',
            'blocked_by_viewer',
            'country_block',
            'followed_by_viewer',
            'follows_viewer',
            'has_channel',
            'has_blocked_viewer', 
            'highlight_reel_count',
            'has_requested_viewer',
            'is_business_account',
            'is_joined_recently',
            'business_category_name',
            'business_email',
            'business_phone_number',
            'business_address_json',
            'requested_by_viewer',
            'connected_fb_page'
        ]
        if prop in standart_properties:
            self.__setattr__(prop, value)   
        
        if prop == 'edge_follow':
            self.follows_count = array[prop]['count'] \
                if array[prop]['count'] is not None  else 0

        if prop == 'edge_followed_by':
            self.followed_by_count = array[prop]['count'] \
                if array[prop]['count'] is not None else 0

        if prop == 'edge_owner_to_timeline_media':
            self._init_media(array[prop])

    def _init_media(self, array):
        self.media_count = array['count'] if 'count' in array.keys() else 0 

        try:
            nodes = array['edges']
        except:
            return

        if not self.media_count or isinstance(nodes, list):
            return

        for media_array in nodes:
            media = Media(media_array['node'])
            if isinstance(media, Media):
                self.add_media(media)
                
class Comment(InitializerModel):
    """
     * @param $value
     * @param $prop
     """

    def __init__(self, props=None):
        self.identifier = None
        self.text = None
        self.created_at = None
        self.edge_liked_by = None
        self.viewer_has_liked = None
        # Account object
        self.owner = None
        

        super(Comment, self).__init__(props)

    def _init_properties_custom(self, value, prop, array):

        if prop == 'id':
           self.identifier = value

        standart_properties = [
            'created_at',
            'text',
            'edge_liked_by'['count'],
        ]

        if prop in standart_properties:
            self.__setattr__(prop, value)

        if prop == 'owner':
            self.owner = Account(value)
        
        #if prop == 'edge_liked_by':
        #    print(array([prop]['edge_liked_by']['count']))\
        #        if array[prop]['count'] is not None else 0
            #self.edge_liked_by = 
class Media(InitializerModel):
    TYPE_IMAGE = 'image'
    TYPE_VIDEO = 'video'
    TYPE_SIDECAR = 'sidecar'
    TYPE_CAROUSEL = 'carousel'

    def __init__(self, props=None):
        self.identifier = None
        self.short_code = None
        self.created_time = 0
        self.type = None
        self.link = None
        self.image_low_resolution_url = None
        self.image_thumbnail_url = None
        self.image_standard_resolution_url = None
        self.image_high_resolution_url = None
        self.square_images = []
        self.carousel_media = []
        self.caption = None
        self.is_ad = False
        self.video_low_resolution_url = None
        self.video_standard_resolution_url = None
        self.video_low_bandwidth_url = None
        self.video_views = 0
        self.video_url = None
        # account object
        self.owner = None
        self.likes_count = 0
        self.location_id = None
        self.location_name = None
        self.comments_count = 0
        self.comments = []
        self.has_more_comments = False
        self.comments_next_page = None
        self.location_slug = None

        super(Media, self).__init__(props)


    def __str__(self):
        string = f"""
        Media Info:
        'Id: {self.identifier}
        Shortcode: {self.short_code}
        Created at: {self.created_time}
        Caption: {self.caption}
        Number of comments: {self.comments_count if hasattr(self,
                                                            'commentsCount') else 0}
        Number of likes: {self.likes_count}
        Link: {self.link}
        Hig res image: {self.image_high_resolution_url}
        Media type: {self.type}
        """

        return textwrap.dedent(string)

    def _init_properties_custom(self, value, prop, arr):

        if prop == 'id':
            self.identifier = value

        standart_properties = [
            'type',
            'link',
            'thumbnail_src',
            'caption',
            'video_view_count',
            'caption_is_edited',
            'is_ad'
        ]

        if prop in standart_properties:
            self.__setattr__(prop, value)

        elif prop == 'created_time' or prop == 'taken_at_timestamp' or prop == 'date':
            self.created_time = int(value)

        elif prop == 'code':
            self.short_code = value
            self.link = get_media_page_link(self.short_code)

        elif prop == 'comments':
            self.comments_count = arr[prop]['count']
        elif prop == 'likes':
            self.likes_count = arr[prop]['count']

        elif prop == 'display_resources':
            medias_url = []
            for media in value:
                medias_url.append(media['src'])

                if media['config_width'] == 640:
                    self.image_thumbnail_url = media['src']
                elif media['config_width'] == 750:
                    self.image_low_resolution_url = media['src']
                elif media['config_width'] == 1080:
                    self.image_standard_resolution_url = media['src']

        elif prop == 'display_src' or prop == 'display_url':
            self.image_high_resolution_url = value
            if self.type is None:
                self.type = Media.TYPE_IMAGE

        elif prop == 'thumbnail_resources':
            square_images_url = []
            for square_image in value:
                square_images_url.append(square_image['src'])
            self.square_images = square_images_url

        elif prop == 'carousel_media':
            self.type = Media.TYPE_CAROUSEL
            self.carousel_media = []
            for carousel_array in arr["carousel_media"]:
                self.set_carousel_media(arr, carousel_array)

        elif prop == 'video_views':
            self.video_views = value
            self.type = Media.TYPE_VIDEO

        elif prop == 'videos':
            self.video_low_resolution_url = arr[prop]['low_resolution']['url']
            self.video_standard_resolution_url = \
            arr[prop]['standard_resolution']['url']
            self.video_low_bandwith_url = arr[prop]['low_bandwidth']['url']

        elif prop == 'video_resources':
            for video in value:
                if video['profile'] == 'MAIN':
                    self.video_standard_resolution_url = video['src']
                elif video['profile'] == 'BASELINE':
                    self.video_low_resolution_url = video['src']
                    self.video_low_bandwith_url = video['src']

        elif prop == 'location' and value is not None:
            self.location_id = arr[prop]['id']
            self.location_name = arr[prop]['name']
            self.location_slug = arr[prop]['slug']

        elif prop == 'user' or prop == 'owner':
            self.owner = Account(arr[prop])

        elif prop == 'is_video':
            if bool(value):
                self.type = Media.TYPE_VIDEO

        elif prop == 'video_url':
            self.video_standard_resolution_url = value

        elif prop == 'shortcode':
            self.short_code = value
            self.link = get_media_page_link(self.short_code)

        elif prop == 'edge_media_to_comment':
            try:
                self.comments_count = int(arr[prop]['count'])
            except KeyError:
                pass
            try:
                edges = arr[prop]['edges']

                for comment_data in edges:
                    self.comments.append(Comment(comment_data['node']))
            except KeyError:
                pass
            try:
                self.has_more_comments = bool(
                    arr[prop]['page_info']['has_next_page'])
            except KeyError:
                pass
            try:
                self.comments_next_page = str(
                    arr[prop]['page_info']['end_cursor'])
            except KeyError:
                pass

        elif prop == 'edge_media_preview_like':
            self.likes_count = arr[prop]['count']
        elif prop == 'edge_liked_by':
            self.likes_count = arr[prop]['count']

        elif prop == 'edge_media_to_caption':
            try:
                self.caption = arr[prop]['edges'][0]['node']['text']
            except (KeyError, IndexError):
                pass

        elif prop == 'edge_sidecar_to_children':
            pass
            
        elif prop == '__typename':
            if value == 'GraphImage':
                self.type = Media.TYPE_IMAGE
            elif value == 'GraphVideo':
                self.type = Media.TYPE_VIDEO
            elif value == 'GraphSidecar':
                self.type = Media.TYPE_SIDECAR

class Instagram:
    HTTP_NOT_FOUND = 404
    HTTP_OK = 200
    HTTP_FORBIDDEN = 403
    HTTP_BAD_REQUEST = 400
    MAX_COMMENTS_PER_REQUEST = 300
    PAGING_TIME_LIMIT_SEC = 1800
    PAGING_DELAY_MINIMUM_MICROSEC = 1000000  # 1 sec min delay to simulate browser
    PAGING_DELAY_MAXIMUM_MICROSEC = 3000000  # 3 sec max delay to simulate browser

    instance_cache = None

    def __init__(self, sleep_between_requests=0):
        self.__req = HTMLSession()
        self.paging_time_limit_sec = Instagram.PAGING_TIME_LIMIT_SEC
        self.paging_delay_minimum_microsec = Instagram.PAGING_DELAY_MINIMUM_MICROSEC
        self.paging_delay_maximum_microsec = Instagram.PAGING_DELAY_MAXIMUM_MICROSEC
        self.session_username = None
        self.session_password = None
        self.cookie=None
        self.user_session = None
        self.rhx_gis = None
        self.sleep_between_requests = sleep_between_requests
        self.user_agent = 'Instagram 126.0.0.25.121 Android (23/6.0.1; 320dpi; 720x1280; samsung; SM-A310F; a3xelte; samsungexynos7580; en_GB; 110937453)'

    def set_cookies(self,cookie):
        cj = http.cookiejar.MozillaCookieJar(cookie)
        cj.load()
        cookie = requests.utils.dict_from_cookiejar(cj)
        self.cookie=cookie
        self.user_session = cookie

    def with_credentials(self, username, password, session_folder=None):
        """
        param string username
        param string password
        param null sessionFolder

        return Instagram
        """
        Instagram.instance_cache = None

        if not session_folder:
            cwd = os.getcwd()
            session_folder = cwd + os.path.sep + 'sessions' + os.path.sep

        if isinstance(session_folder, str):

            Instagram.instance_cache = CookieSessionManager(
                session_folder, slugify(username) + '.txt')

        else:
            Instagram.instance_cache = session_folder

        Instagram.instance_cache.empty_saved_cookies()

        self.session_username = username
        self.session_password = password

    def get_user_agent(self):
        return self.user_agent

    def set_user_agent(self, user_agent):
        self.user_agent = user_agent

    def generate_headers(self, session, gis_token=None):
        """
        :param session: user session dict
        :param gis_token: a token used to be verified by instagram in header
        :return: header dict
        """
        headers = {}
        if session is not None:
            cookies = ''

            for key in session.keys():
                cookies += f"{key}={session[key]}; "

            csrf = session['x-csrftoken'] if session['csrftoken'] is None else \
                session['csrftoken']

            headers = {
                'cookie': cookies,
                'referer': BASE_URL + '/',
                'x-csrftoken': csrf
            }

        if self.user_agent is not None:
            headers['user-agent'] = self.user_agent

            if gis_token is not None:
                headers['x-instagram-gis'] = gis_token

        return headers

    def __generate_gis_token(self, variables):
        """
        :param variables: a dict used to  generate_gis_token
        :return: a token used to be verified by instagram
        """
        rhx_gis = self.__get_rhx_gis() if self.__get_rhx_gis() is not None else 'NULL'
        string_to_hash = ':'.join([rhx_gis, json.dumps(variables, separators=(',', ':')) if isinstance(variables, dict) else variables])
        return hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()

    def __get_rhx_gis(self):
        """
        :return: a string to generate gis_token
        """
        if self.rhx_gis is None:
            try:
                shared_data = self.__get_shared_data_from_page()
            except Exception as _:
                raise InstagramException('Could not extract gis from page')

            if 'rhx_gis' in shared_data.keys():
                self.rhx_gis = shared_data['rhx_gis']
            else:
                self.rhx_gis = None

        return self.rhx_gis

    def __get_mid(self):
        """manually fetches the machine id from graphQL"""
        time.sleep(self.sleep_between_requests)
        response = self.__req.get('https://www.instagram.com/web/__mid/')

        if response.status_code != Instagram.HTTP_OK:
            raise InstagramException.default(response.text,
                                             response.status_code)

        return response.text

    def __get_shared_data_from_page(self, url=BASE_URL):
        """
        :param url: the requested url
        :return: a dict extract from page
        """
        url = url.rstrip('/') + '/'
        time.sleep(self.sleep_between_requests)
        response = self.__req.get(url, headers=self.generate_headers(
            self.user_session))

        if Instagram.HTTP_NOT_FOUND == response.status_code:
            raise InstagramException(f"Page {url} not found")

        if not Instagram.HTTP_OK == response.status_code:
            raise InstagramException.default(response.text,
                                             response.status_code)

        return Instagram.extract_shared_data_from_body(response.text)

    @staticmethod
    def extract_shared_data_from_body(body):
        """
        :param body: html string from a page
        :return: a dict extract from page
        """
        array = re.findall(r'_sharedData = .*?;</script>', body)
        if len(array) > 0:
            raw_json = array[0][len("_sharedData ="):-len(";</script>")]

            return json.loads(raw_json)

        return None

    

    def get_media_comments_by_code(self, code, count=10, max_id=''):
        """
        :param code: media code
        :param count: the number of how many comments you want to get
        :param max_id: used to paginate
        :return: Comment List
        """
        abc = 0
        comments = []
        likedpost = []
        comlikes = []
        index = 0
        has_previous = True

        while has_previous and index < count:
            number_of_comments_to_receive = 0
            if count - index > Instagram.MAX_COMMENTS_PER_REQUEST:
                number_of_comments_to_receive = Instagram.MAX_COMMENTS_PER_REQUEST
            else:
                number_of_comments_to_receive = count - index

            variables = {
                "shortcode": str(code),
                "first": str(number_of_comments_to_receive),
                "after": '' if not max_id else max_id
            }

            comments_url = get_comments_before_comments_id_by_code(
                variables)

            time.sleep(20)
            response = self.__req.get(comments_url,
                                      headers=self.generate_headers(
                                          self.user_session,
                                          self.__generate_gis_token(variables)))

            if not response.status_code == Instagram.HTTP_OK:
                print(response.status_code)
                print(response.text)
                break
                
            jsonResponse = response.json()

            nodes = jsonResponse['data']['shortcode_media']['edge_media_to_parent_comment']['edges']

            for commentArray in nodes:
                comment = Comment(commentArray['node'])
                likedpost.append(commentArray['node']['viewer_has_liked'])
                #comlikes.append(commentArray['node']['edge_liked_by']['count'])
                comments.append(comment)
                tnodes = commentArray['node']['edge_threaded_comments']['edges']
                for tcommentArray in tnodes:
                    tcomment = Comment(tcommentArray['node'])
                    likedpost.append(tcommentArray['node']['viewer_has_liked'])
                    #comlikes.append(tcommentArray['node']['edge_liked_by']['count'])
                    comments.append(tcomment)
                index += 1

            has_previous = jsonResponse['data']['shortcode_media']['edge_media_to_parent_comment']['page_info']['has_next_page']

            number_of_comments = jsonResponse['data']['shortcode_media']['edge_media_to_parent_comment']['count']
            if count > number_of_comments:
                count = number_of_comments

            max_id = jsonResponse['data']['shortcode_media']['edge_media_to_parent_comment']['page_info']['end_cursor']

            abc +=1
            print('total request amount: ',abc)
            print(len(comments))
            if len(nodes) == 0:
                break

        data = {}
        data['next_page'] = max_id
        data['comments'] = comments
        data['liked_post'] = likedpost
        #data['amlikes'] = comlikes
        return data
    
    def is_logged_in(self, session):
            """
            :param session: session dict
            :return: bool
            """
            if self.cookie!=None:
                return True

            if session is None or 'sessionid' not in session.keys():
                return False


            session_id = session['sessionid']
            csrf_token = session['csrftoken']

            headers = {
                'cookie': f"ig_cb=1; csrftoken={csrf_token}; sessionid={session_id};",
                'referer': BASE_URL + '/',
                'x-csrftoken': csrf_token,
                'X-CSRFToken': csrf_token,
                'user-agent': self.user_agent,
            }

            time.sleep(self.sleep_between_requests)
            response = self.__req.get(BASE_URL, headers=headers)

            if not response.status_code == Instagram.HTTP_OK:
                return False

            cookies = response.cookies.get_dict()


            if cookies is None or not 'ds_user_id' in cookies.keys():
                return False

            return True

    def login(self, force=False, two_step_verificator=None):
        """support_two_step_verification true works only in cli mode - just run login in cli mode - save cookie to file and use in any mode
        :param force: true will refresh the session
        :param two_step_verificator: true will need to do verification when an account goes wrong
        :return: headers dict
        """
        if self.session_username is None or self.session_password is None:
            raise InstagramException("User credentials not provided")

        session = json.loads(
            Instagram.instance_cache.get_saved_cookies()) if Instagram.instance_cache.get_saved_cookies() != None else None

        if force or not self.is_logged_in(session):
            time.sleep(self.sleep_between_requests)
            response = self.__req.get(BASE_URL)
            if not response.status_code == Instagram.HTTP_OK:
                raise InstagramException.default(response.text,
                                                 response.status_code)

            match = re.findall(r'"csrf_token":"(.*?)"', response.text)

            if len(match) > 0:
                csrfToken = match[0]

            cookies = response.cookies.get_dict()
            
            mid = self.__get_mid()

            headers = {
                'cookie': f"ig_cb=1; csrftoken={csrfToken}; mid={mid};",
                'referer': BASE_URL + '/',
                'x-csrftoken': csrfToken,
                'X-CSRFToken': csrfToken,
                'user-agent': self.user_agent,
            }
            payload = {'username': self.session_username,
                       'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{self.session_password}"}
            response = self.__req.post(LOGIN_URL, data=payload,
                                       headers=headers)

            if not response.status_code == Instagram.HTTP_OK:
                if (
                        response.status_code == Instagram.HTTP_BAD_REQUEST):
                    print('checkpoint required')

                elif response.status_code is not None and response.text is not None:
                    raise InstagramException(
                        f'Response code is {response.status_code}. Body: {response.text} Something went wrong. Please report issue.',
                        response.status_code)
                else:
                    raise InstagramException(
                        'Something went wrong. Please report issue.',
                        response.status_code)
            elif not response.json()['authenticated']:
                raise InstagramException('User credentials are wrong.')

            cookies = response.cookies.get_dict()

            cookies['mid'] = mid
            Instagram.instance_cache.set_saved_cookies(json.dumps(cookies, separators=(',', ':')))

            self.user_session = cookies

        else:
            self.user_session = session

        return self.generate_headers(self.user_session)


list_text = []
list_owner = []
list_likedpost = []
list_comlikes = []
instagram = Instagram()
instagram.with_credentials('USERNAME', 'PASWORT')
instagram.login()
comments = instagram.get_media_comments_by_code('POSTCODE',10)
for comment in comments['comments']:
    print(comment.edge_liked_by['count'])
#    list_text.append(comment.text)
    list_owner.append(comment.owner.username)
for i in comments['liked_post']:
    list_likedpost.append(i)
#for i in comments['amlikes']:
#    list_comlikes.append(i)

df= pd.DataFrame()
for i in range(len(list_text)):
    list_text[i]=demojize(list_text[i],'de', delimiters=(" ", " "))
#df['text'] = list_text
df['owner'] = list_owner
#df['likes on comment']= list_comlikes
df['owner liked post']= list_likedpost
print(df)
#df.to_csv('/Users/text/excel/ig-commengts.csv', encoding='utf-8', index=True)
#return(df)
