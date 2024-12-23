import transformers
import torch

model_id = "meta-llama/Llama-3.1-8B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.float32},
    device_map="auto",
)


prompt = """Parse this resume into a focused JSON format. Extract only the most important information.
        
        CRITICAL RULES:
        1. Return ONLY valid JSON - no explanations or other text
        2. All arrays must be properly formatted with NO extra commas or braces
        3. Use "Not specified" for missing values instead of null or empty strings
        4. Never include trailing commas in arrays or objects
        5. All strings must use double quotes, not single quotes
        6. Each skill, certification, and achievement must be a separate entry in its array
        7. Check for skills synonyms eg Competencies, Skills, Technologies, Tools, etc. and consolidate them into a single skill entry
        8. Dont take skills from experience section, take them from skills section
        9. Skills must be individual entries for proper node creation 
        10. Dont take skills from experience section, take them from skills section
        11. If its a big line of text, take keywords from it.

        Expected Structure:
        {{
            "name": "Candidate full name",
            "education": [
                {{
                    "degree": "Exact degree name",
                    "field": "Field of study",
                    "institution": "Institution name",
                    "year": "YYYY or YYYY-YYYY format"
                }}
            ],
            "experience": [
                {{
                    "designation": "Exact job title",
                    "work_at": "Company name",
                    "years": "YYYY-YYYY or YYYY-Present",
                    "worked_on": "Technologies worked on"
                }}
            ],
            "number_of_years_of_experience": <integer>,
            "professional_skills": [
                "Individual Skill 1",
                "Individual Skill 2"
            ],
            "certifications": [
                {{
                    "name": "Individual certification name",
                    "year": "YYYY or Not specified",
                    "id": "ID or Not specified"
                }}
            ],
            "languages": [
                "Individual Language 1",
                "Individual Language 2"
            ],
            "projects": [
                {{
                    "name": "Project name",
                    "skills_used": "Technologies used"
                }}
            ],
            "achievements": [
                "Individual Achievement 1",
                "Individual Achievement 2"
            ],
            "DOB": "YYYY-MM-DD or Not specified",
            "gender": "Gender or Not specified",
            "marital_status": "Status or Not specified",
            "nationality": "Nationality or Not specified",
            "current_position": "Current job title",
            "current_employer": "Current employer name"
        }}"""


resume_text = """
{'General': 'Microsoft AZURE FUNDAMENTALS oad Kalim Nabban khan kalim9532@gmail.com Mob :7045463547 To seek a challenging position in the IT infrastructure industry in project planning, implementation, Management and Technical support that utilizes my technical expertise, management skills and enhances the productivity of an esteemed organization. Professional Synopsis A dynamic professional with over 4 years of experience in Server Management and Technical Support. “Presently associated with Dixit Infotech Services PVT LTD From 29rd April 2022 to till date as Windows Administrator. Extensive experience in installation, administration and networking in various environments.. “ Thorough knowledge of Windows Server 2003; Windows Server 2008; Windows Server 2012; VMware/vSphere. “ Active Directory Services; Active Directory Group Policy Objects (GPO); Group Policy Management Console (GPMC); DHCP; WINS; and DNS: data backup, Virtualization Project. Certifications “Certified Microsoft Azure (AZ-900) ¢ = NCP-MCI (Nutanix Certified Professional - Multi Cloud Infrastructure) os CCNA Cisco Certified Network Associate from IP SOLUTION Core Competencies os os os os Server Management Implementing, Administering Windows Server Services. Use of Forensic Tools, Maintenance & Troubleshooting of Windows Servers. Hands on experience with all flavors of windows server operating system. Good working exposure on File Server, Quota MAnagement. Monitor and review system logs and detect and troubleshoot problems. Resolve escalated customer satisfaction issues and work with system administrators to develop escalation procedures. Create technical documentation for a technical audience. Deploy, Configure, Maintain Compute on Azure Cloud. Creating VM in NUTANIX. Creation of data protection. Creating a snapshot policy of VM on nutanix. Performing Active directory Users bulk modification. Deploying Group Policy and security filtering. Managing FSMO Roles transfer / seizing. Performing Active directory demote and promote. Troubleshoot NUTANIX related issues. Develop and maintain knowledge base articles. Perform planned server reboots for post patching activity. Collect server information for migration planning. Validate new built machines and certify for production. Troubleshoot issues related to infrastructure, server configuration. Coordinate with the concern team for Storage and Unix Admin Activities. Hands-on experience in Microsoft Active Directory, DNS, DHCP, IIS and Group Policy Management, Creating a windows server Domain Controller. Ensured that all tickets and phone calls are handled within appropriate service level agreement time frames. Managed NUTANIX environments for non-critical applications and DR Sessions. Proactively monitored customer trouble tickets. Employment Record e From 27" MAY 2019 to 2"? December 2021 with Icon Technologies as NOC Engineer. Job Profile e Supporting as a NOC Engineer. Record ❖ From 27 th MAY 2019 to 2 nd December 2021 with Icon Technologies as NOC Engineer. Job Proﬁle ❖ Supportng as a NOC Engineer. ❖ Managing virtual machines using Hyper V manager, V-Center and Azure Portal. ❖ Security patching of Windows Server machines on DMZ environment monthly as part of Patch Management. ❖ Provided technical support for all customers and ﬁeld support engineers to help solve critcal issues. ❖ Managing Actve directory, DNS and DHCP. ❖ Acve directory Users and Computers bulk modiﬁcaton. ❖ Group Policy and security ﬁltering. ❖ Actve directory replicaon. ❖ DNS installaon and conﬁguraton ❖ DNS zones and record creaton. ❖ DHCP Scope creaton and DHCP MAC binding, Security ﬁltering and IP Reservaon. ❖ Creatng and managing actve directory objects, like user, group, OU. ❖ Using Autotask Incident/SRM/Change Management Tool. ❖ Monitoring and managing server performance ❖ Managing PIM for Local administratve accounts of the servers covering Windows, Linux and UNIX machines. ❖ Creatng Virtual machines in Azure cloud. ❖ provided technical support to vendors. ❖ AD Replicaton monitoring and regular health checks to be performed. ❖ Perform Security Health Check of Windows servers and other compliance related actvites. Employment Record ❖ From Nov 2018 to April 2019 with KGM Group, Desktop support engineer. Job Proﬁle ❖ Windows Desktop conﬁguraton and installaton. ❖ Replace Hardware components from desktop and laptop. ❖ Formated Computers and laptops. ❖ To support daily technical support actvites for desktop, and data management. ❖ To perform the system changes adhered to organizatonal policies ❖ Maintain technical documentaton in associaton with other functonal departments. ❖ Install and maintain equipment and sotware. ❖ Conﬁgured the system based on client policy. Scholastcs . ❖ Bachelors of Science in Computer science (B.SC - CS), Mumbai University. Personal Dossier Name : Kalim Nabban khan Sex : Male. Date of Birth : 10/12/1997 Address : 2B 10th ﬂoor 1006 Om sai ganesh society Kamraj nagar ghatkopar (E) mumbai 400077. Languages proﬁciency : English, Marathi, Hindi. Marital status : Single. Natonality : Indian. Declaraton:- I hereby declare that the statements and informaton furnished above are correct to the best of my knowledge. I assure you that I will do my best if given the chance. Place :- MUMBAI Signature KALIM NABBAN KHAN“Managing virtual machines using Hyper V manager, V-Center and Azure Portal. “Security patching of Windows Server machines on DMZ environment monthly as part of Patch Management. “Provided technical support for all customers and field support engineers to help solve critical issues. “* Managing Active directory, DNS and DHCP. “* Active directory Users and Computers bulk modification. Group Policy and security filtering. Active directory replication. “DNS installation and configuration “DNS zones and record creation. “ DHCP Scope creation and DHCP MAC binding, Security filtering and IP Reservation. Creating and managing active directory objects, like user, group, OU. Using Autotask Incident/SRM/Change Management Tool. Monitoring and managing server performance Managing PIM for Local administrative accounts of the servers covering Windows, Linux and UNIX machines. Creating Virtual machines in Azure cloud. provided technical support to vendors. AD Replication monitoring and regular health checks to be performed. Perform Security Health Check of Windows servers and other compliance related activities. oO OOo So oS Employment Record “ From Nov 2018 to April 2019 with KGM Group, Desktop support engineer. Job Profile = Windows Desktop configuration and installation. Replace Hardware components from desktop and laptop. Formated Computers and laptops. To support daily technical support activities for desktop, and data management. To perform the system changes adhered to organizational policies Maintain technical documentation in association with other functional departments. Install and maintain equipment and software. Configured the system based on client policy. oo oo ood Scholastics. “Bachelors of Science in Computer science (B.SC - CS), Mumbai University. Personal Dossier Name : Kalim Nabban khan Sex : Male. Date of Birth : 10/12/1997 Address : 2B 10th floor 1006 Om sai ganesh society Kamraj nagar ghatkopar (E) mumbai 400077. Languages proficiency —: English, Marathi, Hindi. Marital status : Single. Nationality : Indian. Declaration:- | hereby declare that the statements and information furnished above are correct to the best of my knowledge. l assure you that | will do my best if given the chance. Place :- MUMBAI Signature KALIM NABBAN KHAN concern team for Storage and Unix Admin Actvites. ❖ Hands-on experience in Microsot Actve Directory, DNS, DHCP, IIS and Group Policy Management, ❖ Creatng a windows server Domain Controller. ❖ Ensured that all tckets and phone calls are handled within appropriate service level agreement tme frames. ❖ Managed NUTANIX environments for non-critcal applicatons and DR Sessions. ❖ Proactvely monitored customer trouble tckets. Employment Record ❖ From 27 th MAY 2019 to 2 nd December 2021 with Icon Technologies as NOC Engineer. Job Proﬁle ❖ Supportng as a NOC Engineer. ❖ Managing virtual machines using Hyper V manager, V-Center and Azure Portal. ❖ Security patching of Windows Server machines on DMZ environment monthly as part of Patch Management. ❖ Provided technical support for all customers and ﬁeld support engineers to help solve critcal issues. ❖ Managing Actve directory, DNS and DHCP. ❖ Actve directory Users and Computers bulk modiﬁcaton. ❖ Group Policy and security ﬁltering. ❖ Actve directory replicaton. ❖ DNS installaton and conﬁguraton ❖ DNS zones and record creaton. ❖ DHCP Scope creaton and DHCP MAC binding, Security ﬁltering and IP Reservaton. ❖ Creatng and managing actve directory objects, like user, group, OU. ❖ Using Autotask Incident/SRM/Change Management Tool. ❖ Monitoring and managing server performance ❖ Managing PIM for Local administratve accounts of the servers covering Windows, Linux and UNIX machines. ❖ Creatng Virtual machines in Azure cloud. ❖ provided technical support to vendors. ❖ AD Replicaton monitoring and regular health checks to be performed. ❖ Perform Security Health Check of Windows servers and other compliance related actvites. Employment Record ❖ From Nov 2018 to April 2019 with KGM Group, Desktop support engineer. Job Proﬁle ❖ Windows Desktop conﬁguraton and installaton. ❖ Replace Hardware components from desktop and laptop. ❖ Formated Computers and laptops. ❖ To support daily technical support actvites for desktop, and data management. ❖ To perform the system changes adhered to organizatonal policies ❖ Maintain technical documentaton in associaton with other functonal departments. ❖ Install and maintain equipment and sotware. ❖ Conﬁgured the system based on client policy. Scholastcs . ❖ Bachelors of Science in Computer science (B.SC - CS), Mumbai University. Personal Dossier Name : Kalim Nabban khan Sex : Male. Date of Birth : 10/12/1997 Address : 2B 10th ﬂoor 1006 Om sai ganesh society Kamraj nagar ghatkopar (E) mumbai 400077. Languages proﬁciency : English, Marathi, Hindi. Marital status : Single. Natonality : Indian. Declaraton:- I hereby declare that the statements and informaton furnished above are correct to the best of my knowledge. I assure you that I will do my best if given the chance. Place :- MUMBAI Signature KALIM NABBAN KHANK alim Nabban khan kalim9532@gmail.com Mob : 7045463547 To seek a challenging positon in the IT infrastructure industry in project planning, implementaton, Management and Technical support that utlizes my technical expertse, management skills and enhances the productvity of an esteemed organizaton. Professional Synopsis ❖ A dynamic professional with over 4 years of experience in Server Management and Technical Support. ❖ Presently associated with Dixit Infotech Services PVT LTD From 29rd April 2022 to tll date as Windows Administrator. ❖ Extensive experience in installaton, administraton and networking in various environments.. ❖ Thorough knowledge of Windows Server 2003; Windows Server 2008; Windows Server 2012; VMware/vSphere. ❖ Actve Directory Services; Actve Directory Group Policy Objects (GPO); Group Policy Management Console (GPMC); DHCP; WINS; and DNS: data backup, Virtualizaton Project. Certﬁcatons ❖ Certﬁed Microsot Azure (AZ-900) ❖ NCP-MCI (Nutanix Certﬁed Professional - Mult Cloud Infrastructure) ❖ CCNA Cisco Certﬁed Network Associate from IP SOLUTION Core Competencies ❖ S erver Management ❖ Implementng, Administering Windows Server Services. ❖ Use of Forensic Tools, Maintenance & Troubleshootng of Windows Servers. ❖ Hands on experience with all ﬂavors of windows server operatng system. ❖ Good working exposure on File Server, Quota MAnagement. ❖ Monitor and review system logs and detect and troubleshoot problems. ❖ Resolve escalated customer satsfacton issues and work with system administrators to develop escalaton procedures. ❖ Create technical documentaton for a technical audience. ❖ Deploy, Conﬁgure, Maintain Compute on Azure Cloud. ❖ Creatng VM in NUTANIX. ❖ Creaton of data protecton. ❖ Creatng a snapshot policy of VM on nutanix. ❖ Performing Actve directory Users bulk modiﬁcaton. ❖ Deploying Group Policy and security ﬁltering. ❖ Managing FSMO Roles transfer / seizing. ❖ Performing Actve directory demote and promote. ❖ Troubleshoot NUTANIX related issues. ❖ Develop and maintain knowledge base artcles. ❖ Perform planned server reboots for post patching actvity. ❖ Collect server informaton for migraton planning. ❖ Validate new built machines and certfy for producton. ❖ Troubleshoot issues related to infrastructure, server conﬁguraton. ❖ Coordinate with the concern team for Storage and Unix Admin Actvites. ❖ Hands-on experience in Microsot Actve Directory, DNS, DHCP, IIS and Group Policy Management, ❖ Creatng a windows server Domain Controller. ❖ Ensured that all tckets and phone calls are handled within appropriate service level agreement tme frames. ❖ Managed NUTANIX environments for non-critcal applicatons and DR Sessions. ❖ Proactvely monitored customer trouble tckets. Employment Record ❖ From 27 th MAY 2019 to 2 nd December 2021 with Icon Technologies as NOC Engineer. Job Proﬁle ❖ Supportng as a NOC Engineer. ❖ Managing virtual machines using Hyper V manager, V-Center and Azure Portal. ❖ Security patching of Windows Server machines on DMZ environment monthly as part of Patch Management. ❖ Provided technical support for all customers and ﬁeld support engineers to help solve critcal issues. ❖ Managing Actve directory, DNS and DHCP. ❖ Actve directory Users and Computers bulk modiﬁcaton. ❖ Group Policy and security ﬁltering. ❖ Actve directory replicaton. ❖ DNS installaton and conﬁguraton ❖ DNS zones and record creaton. ❖ DHCP Scope creaton and DHCP MAC binding, Security ﬁltering and IP Reservaton. ❖ Creatng and managing actve directory objects, like user, group, OU. ❖ Using Autotask Incident/SRM/Change Management Tool. ❖ Monitoring and managing server performance ❖ Managing PIM for Local administratve accounts of the servers covering Windows, Linux and UNIX machines. ❖ Creatng Virtual machines in Azure cloud. ❖ provided technical support to vendors. ❖ AD Replicaton monitoring and regular health checks to be performed. ❖ Perform Security Health Check of Windows servers and other compliance related actvites. Employment Record ❖ From Nov 2018 to April 2019 with KGM Group, Desktop support engineer. Job Proﬁle ❖ Windows Desktop conﬁguraton and installaton. ❖ Replace Hardware components from desktop and laptop. ❖ Formated Computers and laptops. ❖ To support daily technical support actvites for desktop, and data management. ❖ To perform the system changes adhered to organizatonal policies ❖ Maintain technical documentaton in associaton with other functonal departments. ❖ Install and maintain equipment and sotware. ❖ Conﬁgured the system based on client policy. Scholastcs . ❖ Bachelors of Science in Computer science (B.SC - CS), Mumbai University. Personal Dossier Name : Kalim Nabban khan Sex : Male. Date of Birth : 10/12/1997 Address : 2B 10th ﬂoor 1006 Om sai ganesh society Kamraj nagar ghatkopar (E) mumbai 400077. Languages proﬁciency : English, Marathi, Hindi. Marital status : Single. Natonality : Indian. Declaraton:- I hereby declare that the statements and informaton furnished above are correct to the best of my knowledge. I assure you that I will do my best if given the chance. Place :- MUMBAI Signature KALIM NABBAN KHAN'}
"""

messages = [
    {"role": "system", "content": prompt},
    {"role": "user", "content": resume_text},
]

outputs = pipeline(
    messages,
    max_new_tokens=1024,
)
print(outputs[0]["generated_text"][-1])
