# -*- coding: utf-8 -*-

from .common import *


class clientHelper():
	def __init__(self, *args, **kwargs):
		super(clientHelper, self).__init__()
		self.expire_public = 3595 # max. Token-Time (Seconds) before clear the Token and delete Token-File [3595 = 60 Minutes]
		self.tempSTORE = tempSTORE
		self.savePUBLIC = publicSECRET

	def convert_epoch(self, epoch):
		CIPHER = datetime(1970,1,1) + timedelta(seconds=int(epoch))
		return CIPHER.strftime('%d.%m.%Y - %H:%M:%S')

	def check_authtoken(self):
		CODING, forceRenew, SWITCH = False, False, None
		GUARDIA, SECURITY, TIME_UTC = self.tempSTORE, self.savePUBLIC, time.time()
		if preserve(SECURITY) is not None:
			try:
				TOKEN_UTC = (os.path.getmtime(SECURITY) + self.expire_public)
				debug_MS(f"(utilities.check_authtoken) ### SESSION-Time (utc NOW) = {self.convert_epoch(TIME_UTC)} || VALID until (utc SESSION) = {self.convert_epoch(TOKEN_UTC)} ###")
				if TIME_UTC < TOKEN_UTC:
					SWITCH = preserve(SECURITY)['data']['attributes']['token']
					debug_MS("(utilities.check_authtoken) ### NOTHING CHANGED - TOKENFILE IS OKAY ###")
				else:
					debug_MS("(utilities.check_authtoken) ### TIMEOUT FOR TOKEN - DELETE TOKENFILE ###")
					forceRenew = True
			except:
				failing("(utilities.check_authtoken) XXXXX !!! ERROR = TOKENFILE [TOKENFORMAT IS INVALID] = ERROR !!! XXXXX")
				forceRenew = True
		else:
			debug_MS("(utilities.check_authtoken) ### NOTHING FOUND - CREATE TOKENFILE FOR DISCOVERY ###")
			forceRenew = True
		if forceRenew:
			if preserve(SECURITY) is not None:
				shutil.rmtree(GUARDIA, ignore_errors=True)
			CODING = self.track_content(AURA_ACCESS, headers=STONE_HEADERS)
			if CODING:
				debug_MS(f"(utilities.check_authtoken) ***** NEW TOKENFILE CREATED : {CODING} *****")
				if not xbmcvfs.exists(GUARDIA) and not os.path.isdir(GUARDIA):
					xbmcvfs.mkdirs(GUARDIA)
				preserve(SECURITY, CODING)
				SWITCH = CODING['data']['attributes']['token']
		return SWITCH

	def track_several(self, stacks, method='GET', queries='JSON', redirects=True, timeout=5, workers=20):
		COMBI_NEW, number, counter, fixation, = [], len(stacks), 0, requests.Session()
		fixation.mount('https://', HTTPAdapter(pool_connections=int(number), pool_maxsize=int(number), pool_block=True)) # Pool-Verbindungen und -Grösse auf tatsächlichen Inhalt festlegen, um Fehlermeldungen zu vermeiden
		def download(pos, code, link, coident):
			heading = {**STONE_HEADERS, **{'User-Agent': WEB_AGENT, 'Authorization': f"Bearer {coident}"}}
			try:
				resp_uno = fixation.request(method, link, headers=heading, allow_redirects=redirects, timeout=timeout)
				resp_uno.raise_for_status()
				debug_MS(f"(utilities.track_several[1.1]) === POS : {pos} || STATUS : {resp_uno.status_code} || URL : {resp_uno.url} || HEADER : {resp_uno.request.headers} ===")
				return f'{{"Count_2":{pos},"Slug_2":"{code}","Link_2":"{link}",{resp_uno.text[1:-1]}}}'
			except Exception as exc_uno:
				failing(f"(utilities.track_several[1.1]) ERROR - RESPONSE - ERROR ##### POS : {pos} === URL : {link} === FAILURE : {exc_uno} #####")
				if link.endswith('parent_slug=sendungen'):
					try:
						modificato = link.replace('/page/', '/shows/').replace('&parent_slug=sendungen', '')
						resp_due = fixation.request(method, modificato, headers=heading, allow_redirects=redirects, timeout=timeout)
						resp_due.raise_for_status()
						debug_MS(f"(utilities.track_several[1.2]) === POS : {pos} || STATUS : {resp_due.status_code} || URL : {resp_due.url} || HEADER : {resp_due.request.headers} ===")
						return f'{{"Count_2":{pos},"Slug_2":"{code}","Link_2":"{modificato}",{resp_due.text[1:-1]}}}'
					except Exception as exc_due:
						failing(f"(utilities.track_several[1.2]) ERROR - RESPONSE - ERROR ##### POS : {pos} === URL : {modificato} === FAILURE : {exc_due} #####")
				return f'{{"Position":{pos},"Status":"ERROR"}}'
		with ThreadPoolExecutor(max_workers=workers) as executor:
			debug_MS("+++++++++++++++++++++++++++++++++++++++++++++")
			coident = self.check_authtoken()
			picker = [executor.submit(download, single['Count_1'], single['Slug_1'], single['Link_1'], coident) for single in stacks]
			wait(picker, timeout=30, return_when=ALL_COMPLETED)
			for future, section in zip(as_completed(picker), stacks):
				counter += 1
				try:
					COMBI_NEW.append(json.loads(future.result()))
				except Exception as exc_tre:
					if counter == 1:
						dialog.notification(translation(30521).format('DETAILS'), translation(30523).format(exc_tre), f"{artpic}icon.png", 12000)
					failing(f"(utilities.track_several[2]) ERROR - EXEPTION - ERROR ##### POS : {section['Count_1']} === URL : {section['Link_1']} === FAILURE : {exc_tre} #####")
					executor.shutdown()
			if COMBI_NEW:
				matching = [flop for flop in COMBI_NEW[:] if flop.get('Status', 'OOKAY') == 'ERROR']
				if len(matching) == number or len(matching) > 4:
					dialog.notification(translation(30521).format('DETAILS'), translation(30524), f"{artpic}icon.png", 12000)
		return json.dumps(COMBI_NEW, indent=2)

	def track_content(self, url, method='GET', queries='JSON', headers={}, redirects=True, data=None, json=None, timeout=30):
		attempts, ANSWER = 0, None
		if method == 'POST':
			heading = {**headers, **{'User-Agent': WEB_AGENT, 'Authorization': f"Bearer {self.check_authtoken()}"}}
		else: heading = {**headers, **{'User-Agent': WEB_AGENT}}
		while not ANSWER and attempts < 2: # 2 x Pingversuche für den Request ::: zur Überprüfung der Verfügbarkeit der URL
			attempts += 1
			try:
				response = requests.request(method, url, headers=heading, allow_redirects=redirects, data=data, json=json, timeout=timeout)
				ANSWER = response.json() if queries == 'JSON' else response.text if queries == 'TEXT' else response
				debug_MS(f"(utilities.track_content) === CALLBACK === STATUS : {response.status_code} || URL : {response.url} || HEADER : {response.request.headers} || DATA : {data} ===")
				if queries == 'JSON' and not isinstance(ANSWER, list) and ANSWER.get('errors', {}):
					message = (ANSWER.get('errors', {})[0].get('detail', '') or 'NO DETAILS FOUND')
					failing(f"(utilities.track_content) ERROR - RESPONSE - ERROR ##### URL : {url} === DETAILS : {message} #####")
					dialog.notification(translation(30521).format('URL'), translation(30523).format(message), icon, 12000)
					return sys.exit(0)
				response.raise_for_status()
			except Exception as exc: # No JSON object could be decoded
				failing(f"(utilities.track_content) ERROR - EXEPTION - ERROR ##### URL : {url} === FAILURE : {exc} #####")
				dialog.notification(translation(30521).format('URL'), translation(30523).format(exc), icon, 12000)
				time.sleep(2)
				if attempts >= 2: return sys.exit(0)
		return ANSWER
