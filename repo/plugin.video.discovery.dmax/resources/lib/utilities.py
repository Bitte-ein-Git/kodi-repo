# -*- coding: utf-8 -*-

from .common import *


def _header(REFERRER=None, PRODISCO=None, USERTOKEN=None):
	header = {}
	header['Accept'] = '*/*'
	header['Content-Type'] = 'application/json; charset=utf-8'
	header['User-Agent'] = agent_WEB
	header['DNT'] = '1'
	header['Upgrade-Insecure-Requests'] = '1'
	header['Accept-Encoding'] = 'gzip'
	header['Accept-Language'] = 'de-DE,de;q=0.9,en;q=0.8'
	header['sec-ch-ua-platform'] = 'Windows'
	header['Origin'] = BASE_URL[:-1]
	if PRODISCO: # TOKEN // SHOWS // VIDEOS // PLAYBACK
		header['X-Device-Info'] = 'STONEJS/1 (Unknown/Unknown; Unknown/Unknown; Unknown)'
		header['X-disco-client'] = 'Alps:HyogaPlayer:0.0.0'
		header['X-disco-params'] = f"realm={REALM_DISCO}"
		if USERTOKEN: # SHOWS // VIDEOS // PLAYBACK
			header['Authorization'] = f"Bearer {USERTOKEN}"
	if REFERRER: header['Referer'] = REFERRER # LOMA // TOKEN // SHOWS // VIDEOS // PLAYBACK
	return header

class Transmission(object):

	def __init__(self):
		self.maxTokenTime = 595 # max. Token-Time (Seconds) before clear the Token and delete Token-File [595 = 10 Minutes]
		self.tempSTORE_folder = tempSTORE
		self.disco_file = storeSECRET

	def clear_content(self, title, filename=None, foldername=None):
		debug_MS(f"(utilities.clear_content) ### DELETE OLD-FILE : * {title} * ###")
		if filename is not None and xbmcvfs.exists(filename):
			if foldername is not None and xbmcvfs.exists(foldername) and os.path.exists(foldername):
				shutil.rmtree(foldername, ignore_errors=True)

	def save_content(self, title, filename, foldername, notes):
		debug_MS(f"(utilities.save_content) ### SAVE NEW-FILE : * {title} * ###")
		os.makedirs(foldername, exist_ok=True)
		preserve(filename, notes)

	def convert_epoch(self, epoch):
		CIPHER = datetime(1970,1,1) + timedelta(seconds=int(epoch))
		return CIPHER.strftime('%d.%m.%Y - %H:%M:%S')

	def check_FreeToken(self):
		debug_MS("(utilities.check_FreeToken) ##### START check_FreeToken #####")
		CODING, forceRenew, AUTH_TOKEN = False, False, None
		if xbmcvfs.exists(self.disco_file) and os.path.isfile(self.disco_file):
			self.NOW_UTC, self.FILE_UTC = time.time(), (os.path.getmtime(self.disco_file) + self.maxTokenTime)
			debug_MS(f"(utilities.check_FreeToken) ##### SESSION-Time (utc NOW) = {self.convert_epoch(self.NOW_UTC)} || VALID until (utc SESSION) = {self.convert_epoch(self.FILE_UTC)} #####")
			if self.NOW_UTC < self.FILE_UTC:
				try:
					AUTH_TOKEN = preserve(self.disco_file)['data']['attributes']['token']
					debug_MS("(utilities.check_FreeToken) ##### NOTHING CHANGED - TOKENFILE IS OKAY #####")
				except:
					failing("(utilities.check_FreeToken) XXXXX !!! ERROR = TOKENFILE [TOKENFORMAT IS INVALID] = ERROR !!! XXXXX")
					forceRenew = True
			else:
				debug_MS("(utilities.check_FreeToken) ##### TIMEOUT FOR TOKEN - DELETE TOKENFILE #####")
				forceRenew = True
		else:
			debug_MS("(utilities.check_FreeToken) ##### NOTHING FOUND - CREATE TOKENFILE FOR DISCOVERY #####")
			forceRenew = True
		if forceRenew:
			self.clear_content('FREE_SECRET', self.disco_file, self.tempSTORE_folder)
			CODING = self.retrieveContent(ACCESS_URL, forcing=False)
			if CODING:
				debug_MS(f"(utilities.check_FreeToken) ***** NEW TOKENFILE CREATED : {CODING} *****")
				self.save_content('FREE_SECRET', self.disco_file, self.tempSTORE_folder, CODING)
				AUTH_TOKEN = CODING['data']['attributes']['token']
		return AUTH_TOKEN

	def retrieveMultiData(self, MURLS, method='GET', REF=BASE_URL, PRO=True, timeout=5, retries=2):
		COMBI_NEW, number = [], len(MURLS)
		def download(pos, url, token):
			CAPTION = _header(REF, None, None) if url.startswith('https://de-api.loma-cms') else _header(REF, PRO, token)
			UNCHECK = ssl.create_default_context()
			UNCHECK.check_hostname = False
			UNCHECK.verify_mode = ssl.CERT_NONE
			connector = urllib3.PoolManager(block=True, ssl_context=UNCHECK, maxsize=10)
			response = connector.request(method, url, headers=CAPTION, redirect=True, timeout=timeout, retries=retries)
			if response.status in [200, 201, 202]:
				debug_MS(f"(utilities.retrieveMultiData[1]) === POS : {pos} === URL : {url} === HEADER : {CAPTION} ===")
				return f'{{"Position":{pos},"Demand":"{url}",{py3_dec(response.data[1:-1])}}}'
			else:
				failing(f"(utilities.retrieveMultiData[1]) ERROR - RESPONSE - ERROR ##### POS : {pos} === STATUS : {response.status} === URL : {url} === DATA : {py3_dec(response.data)} #####")
				return '{"ERROR_occurred":true}'
		with ThreadPoolExecutor() as executor:
			debug_MS("---------------------------------------------")
			REALCODE = self.check_FreeToken()
			picker = [executor.submit(download, pos, url, REALCODE) for pos, url in MURLS]
			wait(picker, timeout=30, return_when=ALL_COMPLETED)
			for ii, future in enumerate(as_completed(picker), 1):
				try:
					COMBI_NEW.append(json.loads(future.result()))
				except Exception as exc:
					failing(f"(utilities.retrieveMultiData[2]) ERROR - EXEPTION - ERROR ##### FUTURE_CONNECT : {future.result()} === FAILURE : {exc} #####")
					dialog.notification(translation(30521).format('DETAILS', ''), translation(30523).format(exc), icon, 10000)
					executor.shutdown()
			if COMBI_NEW:
				matching = [flop for flop in COMBI_NEW[:] if flop.get('ERROR_occurred', '') is True]
				if len(matching) == number or len(matching) > 3:
					dialog.notification(translation(30521).format('DETAILS', ''), translation(30524), icon, 10000)
			return json.dumps(COMBI_NEW, indent=2)

	def retrieveContent(self, url, method='GET', queries='JSON', REF=BASE_URL, PRO=True, forcing=True, headers={}, redirects=True, verify=False, data=None, json=None, timeout=30):
		attempts, ANSWER = 0, None
		ACTUCODE = self.check_FreeToken() if forcing is True else None
		SPECIFICS = _header(REF, None, None) if url.startswith('https://de-api.loma-cms') else _header(REF, PRO, ACTUCODE)
		while not ANSWER and attempts < 2: # 2 x Pingversuche für den Request ::: zur Überprüfung der Verfügbarkeit der URL
			attempts += 1
			try:
				response = requests.request(method, url, headers=SPECIFICS, allow_redirects=redirects, verify=verify, data=data, json=json, timeout=timeout)
				ANSWER = response.json() if queries == 'JSON' else response.text if queries == 'TEXT' else response
				debug_MS(f"(utilities.retrieveContent) === CALLBACK === STATUS : {response.status_code} || URL : {response.url} || HEADER : {SPECIFICS} || DATA : {data} ===")
				if queries == 'JSON' and not isinstance(response.json(), list) and response.json().get('errors', ''):
					message = (response.json().get('errors', {})[0].get('detail', '') or 'NO DETAILS FOUND')
					failing(f"(utilities.retrieveContent) ERROR - RESPONSE - ERROR ##### URL : {url} === DETAIL : {message} #####")
					dialog.notification(translation(30521).format('URL', ''), translation(30523).format(message), icon, 10000)
					return sys.exit(0)
				response.raise_for_status()
			except Exception as exc: # No JSON object could be decoded
				failing(f"(utilities.retrieveContent) ERROR - EXEPTION - ERROR ##### URL : {url} === FAILURE : {exc} #####")
				dialog.notification(translation(30521).format('URL', ''), translation(30523).format(exc), icon, 10000)
				time.sleep(2)
				if attempts >= 2: return sys.exit(0)
		return ANSWER
