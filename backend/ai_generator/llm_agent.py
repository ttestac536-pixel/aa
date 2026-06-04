import cohere
import json
import os
import zipfile
import io
import uuid
from typing import Tuple, Dict, Any
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def _normalize_ver(version: str) -> str:
    """Enforce OIC version format: 01.00.0000"""
    parts = (version or "01.00.0000").split(".")
    while len(parts) < 3:
        parts.append("0000")
    return f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{parts[2].zfill(4)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _safe_id(name: str, maxlen: int = 50) -> str:
    """Uppercase, replace spaces/dashes with underscores, truncate."""
    return name.upper().replace(" ", "_").replace("-", "_")[:maxlen]


# ---------------------------------------------------------------------------
# ics_project_attributes.properties  (CORRECT KEY NAMES from reference)
# ---------------------------------------------------------------------------

def _make_project_attributes(project_code: str, project_name: str,
                              version: str, description: str,
                              style: str = "MAP_DATA") -> str:
    """
    Uses the EXACT property key names OIC expects, as seen in the
    reference IAR (icspackage/project/.../ics_project_attributes.properties).
    Keys are: project_code, project_name, project_version, etc.
    NOT project.name / project.version (those are wrong).
    """
    version = _normalize_ver(version)
    now_stamp = datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")
    return (
        f"#{now_stamp}\n"
        f"CAV=4\n"
        f"lastUpdatedICSVersion=26.04.0.21-EC\n"
        f"mep_type=MEP00\n"
        f"modelType=FREEFORM\n"
        f"originalICSVersion=26.01.0.13-EC\n"
        f"project_code={project_code}\n"
        f"project_name={project_name}\n"
        f"project_persisted_state=CONFIGURED\n"
        f"project_transient_state=UNLOCKED\n"
        f"project_type=DEVELOPED\n"
        f"project_version={version}\n"
        f"smartTags=\\ style\\:{_style_tag(style)}\n"
        f"tracking_instance_name=IntegrationInstance\n"
        f"version=26.04.0.21\n"
    )


def _style_tag(style: str) -> str:
    mapping = {
        "MAP_DATA": "map data",
        "FREEFORM": "app driven orchestration",
        "SCHEDULED": "scheduled",
        "PUBLISH": "publish to OIC",
        "SUBSCRIBE": "subscribe to OIC",
    }
    return mapping.get(style.upper(), "map data")


# ---------------------------------------------------------------------------
# PROJECT-INF/project.xml  (the real integration definition OIC parses)
# ---------------------------------------------------------------------------

def _make_project_xml(project_code: str, project_name: str, version: str,
                       source_conn_code: str, source_adapter_type: str,
                       target_conn_code: str, target_adapter_type: str,
                       field_mappings: list, description: str) -> str:
    """
    Build the PROJECT-INF/project.xml using the real OIC namespace schema.
    This is the file OIC actually parses for integration logic.
    The reference uses:
      xmlns:ns3="http://www.oracle.com/2014/03/ics/project"
      xmlns:ns2="http://www.oracle.com/2014/03/ics/flow/definition"
    """
    version = _normalize_ver(version)

    # Build XSLT mappings block
    xsl_mappings = _make_xslt_mappings(field_mappings, source_conn_code, target_conn_code)

    # Unique resource IDs (sequential, matching reference pattern)
    src_app = "application_10"
    tgt_app = "application_20"
    proc_meta = "processor_1"
    proc_tracker = "processor_6"
    proc_catch = "processor_30"
    proc_xform = "processor_40"
    rg_meta = "resourcegroup_2"
    rg_src = "resourcegroup_11"
    rg_tgt = "resourcegroup_21"
    rg_xsl = "resourcegroup_41"
    mc_meta = "messagecontext_3"
    mc_src_req = "messagecontext_15"
    mc_tgt_req = "messagecontext_25"
    mc_tgt_resp = "messagecontext_26"
    mc_catch = "messagecontext_31"

    src_adapter_ns = source_adapter_type.lower()
    tgt_adapter_ns = target_adapter_type.lower()

    xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns3:icsproject name="project_1" version="10.1" cversion="5" modelType="freeform"
    xmlns="http://www.oracle.com/2014/03/ics/project/definition"
    xmlns:ns2="http://www.oracle.com/2014/03/ics/flow/definition"
    xmlns:ns3="http://www.oracle.com/2014/03/ics/project">
    <projectCode>{project_code}</projectCode>
    <projectVersion>{version}</projectVersion>
    <projectName>{project_name}</projectName>
    <percentComplete>100</percentComplete>
    <projectHasErrors>false</projectHasErrors>
    <projectHasWarnings>false</projectHasWarnings>
    <description>{description}</description>
    <ns3:icsflow name="flow_1">
        <ns2:application name="{src_app}">
            <ns2:role>source</ns2:role>
            <ns2:adapter>
                <ns2:type>app-adapter</ns2:type>
                <ns2:code>{source_conn_code}</ns2:code>
                <ns2:name>SourceReceive</ns2:name>
                <ns2:property name="hasAttachment" value="false"/>
            </ns2:adapter>
            <ns2:mep>fire-and-forget</ns2:mep>
            <ns2:outbound name="outbound_12">
                <ns2:binding>soap</ns2:binding>
                <ns2:operation>receive</ns2:operation>
                <ns2:resourceGroup name="{rg_src}">
                    <ns2:resource name="resource_13"
                        location="../resources/{src_app}/outbound_12/{rg_src}/SourceReceive_REQUEST.wsdl"
                        type="wsdl"/>
                    <ns2:resource name="resource_14"
                        location="../resources/{src_app}/outbound_12/{rg_src}/SourceReceive_REQUEST.jca"
                        type="jca"/>
                </ns2:resourceGroup>
                <ns2:output name="output_16">
                    <ns2:role>request</ns2:role>
                    <ns2:messageContextRef refUri="{mc_src_req}"/>
                </ns2:output>
            </ns2:outbound>
        </ns2:application>
        <ns2:application name="{tgt_app}">
            <ns2:role>target</ns2:role>
            <ns2:adapter>
                <ns2:type>app-adapter</ns2:type>
                <ns2:code>{target_conn_code}</ns2:code>
                <ns2:name>TargetInvoke</ns2:name>
                <ns2:property name="hasAttachment" value="false"/>
            </ns2:adapter>
            <ns2:mep>push-sync</ns2:mep>
            <ns2:inbound name="inbound_22">
                <ns2:operation>execute</ns2:operation>
                <ns2:resourceGroup name="{rg_tgt}">
                    <ns2:resource name="resource_23"
                        location="../resources/{tgt_app}/inbound_22/{rg_tgt}/TargetInvoke_REQUEST.wsdl"
                        type="wsdl"/>
                    <ns2:resource name="resource_24"
                        location="../resources/{tgt_app}/inbound_22/{rg_tgt}/TargetInvoke_REQUEST.jca"
                        type="jca"/>
                    <ns2:resource name="resource_27"
                        location="../resources/{tgt_app}/inbound_22/{rg_tgt}/ICSFault.xsd"
                        type="xsd"/>
                </ns2:resourceGroup>
                <ns2:input name="input_28">
                    <ns2:role>request</ns2:role>
                    <ns2:messageContextRef refUri="{mc_tgt_req}"/>
                </ns2:input>
                <ns2:output name="output_29">
                    <ns2:role>response</ns2:role>
                    <ns2:messageContextRef refUri="{mc_tgt_resp}"/>
                </ns2:output>
            </ns2:inbound>
        </ns2:application>
        <ns2:processor name="{proc_meta}">
            <ns2:type>integrationMetadata</ns2:type>
            <ns2:role>undefined</ns2:role>
            <ns2:resourceGroup name="{rg_meta}">
                <ns2:resource name="resource_3"
                    location="../resources/{proc_meta}/{rg_meta}/ICSIntegrationMetadata.xsd"
                    type="xsd"/>
            </ns2:resourceGroup>
            <ns2:output name="output_4">
                <ns2:messageContextRef refUri="{mc_meta}"/>
            </ns2:output>
        </ns2:processor>
        <ns2:processor name="{proc_tracker}">
            <ns2:type>messageTracker</ns2:type>
            <ns2:role>messageTracker:global</ns2:role>
            <ns2:trackingVariableGroup>
                <ns2:trackingVariable>
                    <ns2:role>tracking_var_1</ns2:role>
                    <ns2:primary>true</ns2:primary>
                    <ns2:name>IntegrationInstance</ns2:name>
                    <ns2:messageContextRef refUri="{mc_src_req}"/>
                    <ns2:output name="output_7">
                        <ns2:messageContextRef refUri="messagecontext_7"/>
                    </ns2:output>
                </ns2:trackingVariable>
            </ns2:trackingVariableGroup>
        </ns2:processor>
        <ns2:processor name="{proc_catch}">
            <ns2:type>catchAll</ns2:type>
            <ns2:role>undefined</ns2:role>
            <ns2:resourceGroup name="resourcegroup_31">
                <ns2:resource name="resource_32"
                    location="../resources/{proc_catch}/resourcegroup_31/ICSFault.xsd"
                    type="xsd"/>
            </ns2:resourceGroup>
            <ns2:output name="output_33">
                <ns2:messageContextRef refUri="{mc_catch}"/>
            </ns2:output>
        </ns2:processor>
        <ns2:processor name="{proc_xform}">
            <ns2:type>transformer</ns2:type>
            <ns2:role>transformer:request-map</ns2:role>
            <ns2:resourceGroup name="{rg_xsl}">
                <ns2:resource name="resource_42"
                    location="../resources/{proc_xform}/{rg_xsl}/mapping.xsl"
                    type="xslt"/>
            </ns2:resourceGroup>
            <ns2:input name="input_43">
                <ns2:messageContextRef refUri="{mc_src_req}"/>
            </ns2:input>
            <ns2:output name="output_44">
                <ns2:messageContextRef refUri="{mc_tgt_req}"/>
            </ns2:output>
            <ns2:property name="has-mappings" value="true"/>
        </ns2:processor>
        <ns2:messageContext name="{mc_meta}">
            <ns2:resourceRef refUri="{proc_meta}/{rg_meta}/resource_3"/>
            <ns2:rootElement elementName="metadata"
                namespace="http://www.oracle.com/2014/03/ic/integration/metadata"/>
        </ns2:messageContext>
        <ns2:messageContext name="messagecontext_7">
            <ns2:rootElement elementName="string" namespace="http://www.w3.org/2001/XMLSchema"/>
        </ns2:messageContext>
        <ns2:messageContext name="{mc_src_req}">
            <ns2:resourceRef refUri="{src_app}/outbound_12/{rg_src}/resource_13"/>
            <ns2:rootElement elementName="SourceRequest"
                namespace="http://xmlns.oracle.com/cloud/adapter/{src_adapter_ns}/SourceReceive_REQUEST/types"/>
        </ns2:messageContext>
        <ns2:messageContext name="{mc_tgt_req}">
            <ns2:resourceRef refUri="{tgt_app}/inbound_22/{rg_tgt}/resource_23"/>
            <ns2:rootElement elementName="TargetRequest"
                namespace="http://xmlns.oracle.com/cloud/adapter/{tgt_adapter_ns}/TargetInvoke_REQUEST/types"/>
        </ns2:messageContext>
        <ns2:messageContext name="{mc_tgt_resp}">
            <ns2:resourceRef refUri="{tgt_app}/inbound_22/{rg_tgt}/resource_23"/>
            <ns2:rootElement elementName="TargetResponse"
                namespace="http://xmlns.oracle.com/cloud/adapter/{tgt_adapter_ns}/TargetInvoke_REQUEST/types"/>
        </ns2:messageContext>
        <ns2:messageContext name="{mc_catch}">
            <ns2:resourceRef refUri="{proc_catch}/resourcegroup_31/resource_32"/>
            <ns2:rootElement elementName="fault"
                namespace="http://www.oracle.com/2014/03/ics/fault"/>
        </ns2:messageContext>
        <ns2:commonNamespaceMaps/>
        <ns2:orchestration>
            <ns2:integrationMetadata id="im0" refUri="{proc_meta}"/>
            <ns2:globalTry id="gt0">
                <ns2:receive trackingRefUri="{proc_tracker}" id="r0"
                    refUri="{src_app}/outbound_12/output_16"/>
                <ns2:transformer id="m0" refUri="{proc_xform}"/>
                <ns2:invoke id="i0" refUri="{tgt_app}" name="TargetInvoke"/>
                <ns2:stop id="st0"/>
                <ns2:catchAll id="ta0" refUri="{proc_catch}">
                    <ns2:ehStop id="eh0"/>
                </ns2:catchAll>
            </ns2:globalTry>
        </ns2:orchestration>
    </ns3:icsflow>
</ns3:icsproject>"""
    return xml


# ---------------------------------------------------------------------------
# PROJECT-INF/analysis.json
# ---------------------------------------------------------------------------

def _make_analysis_json(project_code: str, version: str) -> str:
    version = _normalize_ver(version)
    data = {
        "id": f"{project_code}_{version}",
        "icsProject": {
            "version": version,
            "percentageComplete": 100,
            "modelType": "FREEFORM",
            "projectCode": project_code,
            "processorCount": {
                "INTEGRATION_METADATA": 1,
                "MESSAGE_TRACKER": 1,
                "CATCH_ALL": 1,
                "TRANSFORMER": 1,
                "SOURCE": 1,
                "TARGET": 1
            },
            "smartTags": "style:map data"
        }
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# PROJECT-INF/layout3.json
# ---------------------------------------------------------------------------

def _make_layout_json() -> str:
    data = {
        "savedInSpectra": True,
        "chosenLayout": "HorizontalLayout",
        "inGlobalTry": False,
        "globalCatchAll": {"children": []},
        "children": [
            {"id": "r0", "open": "open", "chosenLayout": "HorizontalLayout", "inGlobalTry": True},
            {"id": "m0", "open": "open", "chosenLayout": "HorizontalLayout", "inGlobalTry": True},
            {"id": "i0", "open": "open", "chosenLayout": "HorizontalLayout", "inGlobalTry": True},
            {"id": "ta0", "open": "open", "chosenLayout": "HorizontalLayout", "inGlobalTry": False}
        ]
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# PROJECT-INF/project_messages.json
# ---------------------------------------------------------------------------

def _make_project_messages_json() -> str:
    data = {
        "messages": {
            "@class": "java.util.HashMap",
            "": ["java.util.ArrayList", []],
            "r0": ["java.util.ArrayList", []],
            "m0": ["java.util.ArrayList", []],
            "i0": ["java.util.ArrayList", []],
            "ta0": ["java.util.ArrayList", []]
        }
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# ApplicationInstance XML (correct format for icspackage/appinstances/)
# ---------------------------------------------------------------------------

def _make_app_instance_xml(conn_code: str, display_name: str,
                            adapter_type: str, host: str, port: str,
                            extra: dict, role: str = "SOURCE_AND_TARGET") -> str:
    """
    Build an ApplicationInstance XML matching the real OIC format.
    Uses namespace http://xmlns.oracle.com/adapters/cloud.
    This goes in icspackage/appinstances/<CONN_CODE>.xml
    """
    instance_id = str(uuid.uuid4())
    group_id = str(uuid.uuid4())
    now = _now_iso()
    adapter_type_lower = adapter_type.lower()

    # Build connection properties based on adapter type
    conn_props = _build_conn_properties(adapter_type_lower, host, port, extra)

    security_policy = _get_security_policy(adapter_type_lower)

    return f"""<?xml version = '1.0' encoding = 'UTF-8'?>
<ns2:ApplicationInstance xmlns:ns2="http://xmlns.oracle.com/adapters/cloud">  <id>{instance_id}</id>  <instanceCode>{conn_code}</instanceCode>  <groupId>{group_id}</groupId>  <displayName>{display_name}</displayName>  <applicationTypeRef>{adapter_type_lower}</applicationTypeRef>  <description/>  <connectionProperties>{conn_props}  </connectionProperties>  <securityPolicy>{security_policy}</securityPolicy>  <revision>01.00.0000</revision>  <status>CONFIGURED</status>  <hidden>false</hidden>  <percentageComplete>100</percentageComplete>  <attachments/>  <privateEndpoint>false</privateEndpoint>  <publicScope>false</publicScope>  <hasOverride>false</hasOverride>  <pluginVersion>23.3.5</pluginVersion>  <updatePluginVersion>23.3.5</updatePluginVersion>  <integrationRole>{role}</integrationRole>  <securedAuditInfo>    <auditInfo>      <createdBy>icsadmin</createdBy>      <lastUpdatedBy>icsadmin</lastUpdatedBy>      <lastUpdatedDate>{now}</lastUpdatedDate>      <createdDate>{now}</createdDate>    </auditInfo>    <lockInfo>      <lockedBy>icsadmin</lockedBy>      <lockedDate>{now}</lockedDate>    </lockInfo>  </securedAuditInfo></ns2:ApplicationInstance>"""


def _build_conn_properties(adapter_type: str, host: str, port: str,
                            extra: dict) -> str:
    """Build connectionProperty elements for common adapter types."""
    props = []

    def prop(name, value=""):
        v = f"<value>{value}</value>" if value else ""
        props.append(f"    <connectionProperty>      <name>{name}</name>      {v}    </connectionProperty>")

    if adapter_type in ("sftp", "ftp"):
        prop("host", host)
        prop("port", port)
        prop("integration_role", "SOURCE_AND_TARGET")
        prop("connectionType", "sftp" if adapter_type == "sftp" else "ftp")
        for k, v in extra.items():
            prop(k, str(v))
        prop("csfkey", "%%{}_csfkey".format(host.replace(".", "_").upper()))
        prop("csfMap", "oracle.cloud.adapter")
    elif adapter_type in ("oracle", "erp", "oracledb", "db"):
        prop("Host", "%%{}_Host".format(host.replace(".", "_").upper()))
        prop("targetWSDLURL", f"%%{host.replace('.','_').upper()}_targetWSDLURL")
        prop("integration_role", "SOURCE_AND_TARGET")
        prop("serviceEndpoints", f"%%{host.replace('.','_').upper()}_serviceEndpoints")
        prop("csfkey", f"%%{host.replace('.','_').upper()}_csfkey")
        prop("csfMap", "oracle.cloud.adapter")
        for k, v in extra.items():
            prop(k, str(v))
    elif adapter_type == "rest":
        prop("connectionUrl", f"%%{host.replace('.','_').upper()}_connectionUrl")
        prop("connectionType", "restUrl")
        prop("integration_role", "SOURCE_AND_TARGET")
        prop("csfkey", f"%%{host.replace('.','_').upper()}_csfkey")
        prop("csfMap", "oracle.cloud.adapter")
        for k, v in extra.items():
            prop(k, str(v))
    elif adapter_type == "soap":
        prop("targetWSDLURL", f"%%{host.replace('.','_').upper()}_targetWSDLURL")
        prop("integration_role", "SOURCE_AND_TARGET")
        for k, v in extra.items():
            prop(k, str(v))
    else:
        prop("host", host)
        prop("port", port)
        prop("integration_role", "SOURCE_AND_TARGET")
        for k, v in extra.items():
            prop(k, str(v))

    return "".join(props)


def _get_security_policy(adapter_type: str) -> str:
    mapping = {
        "sftp": "FTP_PUBLIC_KEY_AUTH",
        "ftp": "FTP_PASSWORD_AUTH",
        "oracle": "USERNAME_PASSWORD_TOKEN",
        "erp": "USERNAME_PASSWORD_TOKEN",
        "oracledb": "USERNAME_PASSWORD_TOKEN",
        "db": "USERNAME_PASSWORD_TOKEN",
        "rest": "BASIC_AUTH",
        "soap": "NONE",
    }
    return mapping.get(adapter_type, "BASIC_AUTH")


# ---------------------------------------------------------------------------
# ICSFault.xsd  (used in catch blocks, required by reference)
# ---------------------------------------------------------------------------

ICS_FAULT_XSD = """<?xml version="1.0" encoding="UTF-8" ?>
<schema xmlns="http://www.w3.org/2001/XMLSchema"
        xmlns:ics="http://www.oracle.com/2014/03/ics/fault"
        targetNamespace="http://www.oracle.com/2014/03/ics/fault"
        elementFormDefault="qualified" version="1">
    <element name="fault" type="ics:faultType"/>
    <complexType name="faultType">
        <sequence>
            <element name="type" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="code" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="message" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="detail" type="string" minOccurs="0" maxOccurs="1"/>
        </sequence>
    </complexType>
</schema>"""

# ---------------------------------------------------------------------------
# ICSIntegrationMetadata.xsd
# ---------------------------------------------------------------------------

ICS_METADATA_XSD = """<?xml version="1.0" encoding="UTF-8" ?>
<schema xmlns="http://www.w3.org/2001/XMLSchema"
        xmlns:ics="http://www.oracle.com/2014/03/ic/integration/metadata"
        targetNamespace="http://www.oracle.com/2014/03/ic/integration/metadata"
        elementFormDefault="qualified" version="1">
    <element name="metadata" type="ics:metadataType"/>
    <complexType name="metadataType">
        <sequence>
            <element name="integration" type="ics:IntegrationType" minOccurs="1" maxOccurs="1"/>
            <element name="runtime" type="ics:RuntimeType" minOccurs="1" maxOccurs="1"/>
            <element name="environment" type="ics:EnvironmentType" minOccurs="1" maxOccurs="1"/>
        </sequence>
    </complexType>
    <complexType name="IntegrationType">
        <sequence>
            <element name="name" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="identifier" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="version" type="string" minOccurs="1" maxOccurs="1"/>
        </sequence>
    </complexType>
    <complexType name="RuntimeType">
        <sequence>
            <element name="instanceId" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="invokedBy" type="string" minOccurs="1" maxOccurs="1"/>
        </sequence>
    </complexType>
    <complexType name="EnvironmentType">
        <sequence>
            <element name="serviceInstanceName" type="string" minOccurs="1" maxOccurs="1"/>
            <element name="baseURL" type="string" minOccurs="1" maxOccurs="1"/>
        </sequence>
    </complexType>
</schema>"""

# ---------------------------------------------------------------------------
# Minimal WSDL stubs (needed so project.xml resource refs resolve)
# ---------------------------------------------------------------------------

def _make_source_wsdl(project_code: str, adapter_type: str) -> str:
    ns = f"http://xmlns.oracle.com/cloud/adapter/{adapter_type.lower()}/SourceReceive_REQUEST"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:tns="{ns}"
             xmlns:types="{ns}/types"
             targetNamespace="{ns}"
             name="SourceReceive_REQUEST">
    <types>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                targetNamespace="{ns}/types">
            <element name="SourceRequest">
                <complexType>
                    <sequence>
                        <element name="payload" type="string" minOccurs="0"/>
                    </sequence>
                </complexType>
            </element>
        </schema>
    </types>
    <message name="SourceRequestMessage">
        <part name="parameters" element="types:SourceRequest"/>
    </message>
    <portType name="SourceReceive_REQUEST_ptt">
        <operation name="receive">
            <input message="tns:SourceRequestMessage"/>
        </operation>
    </portType>
    <binding name="SourceReceive_REQUEST_bnd"
             type="tns:SourceReceive_REQUEST_ptt">
        <soap:binding xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                      style="document"
                      transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="receive">
            <soap:operation xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" soapAction="receive"/>
            <input><soap:body xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" use="literal"/></input>
        </operation>
    </binding>
    <service name="SourceReceive_REQUEST_svc">
        <port name="SourceReceive_REQUEST_pt"
              binding="tns:SourceReceive_REQUEST_bnd">
            <soap:address xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" location="http://localhost"/>
        </port>
    </service>
</definitions>"""


def _make_target_wsdl(project_code: str, adapter_type: str) -> str:
    ns = f"http://xmlns.oracle.com/cloud/adapter/{adapter_type.lower()}/TargetInvoke_REQUEST"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:tns="{ns}"
             xmlns:types="{ns}/types"
             targetNamespace="{ns}"
             name="TargetInvoke_REQUEST">
    <types>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                targetNamespace="{ns}/types">
            <element name="TargetRequest">
                <complexType>
                    <sequence>
                        <element name="payload" type="string" minOccurs="0"/>
                    </sequence>
                </complexType>
            </element>
            <element name="TargetResponse">
                <complexType>
                    <sequence>
                        <element name="result" type="string" minOccurs="0"/>
                    </sequence>
                </complexType>
            </element>
        </schema>
    </types>
    <message name="TargetRequestMessage">
        <part name="parameters" element="types:TargetRequest"/>
    </message>
    <message name="TargetResponseMessage">
        <part name="parameters" element="types:TargetResponse"/>
    </message>
    <portType name="TargetInvoke_REQUEST_ptt">
        <operation name="execute">
            <input message="tns:TargetRequestMessage"/>
            <output message="tns:TargetResponseMessage"/>
        </operation>
    </portType>
    <binding name="TargetInvoke_REQUEST_bnd"
             type="tns:TargetInvoke_REQUEST_ptt">
        <soap:binding xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                      style="document"
                      transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="execute">
            <soap:operation xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" soapAction="execute"/>
            <input><soap:body xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" use="literal"/></input>
            <output><soap:body xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" use="literal"/></output>
        </operation>
    </binding>
    <service name="TargetInvoke_REQUEST_svc">
        <port name="TargetInvoke_REQUEST_pt"
              binding="tns:TargetInvoke_REQUEST_bnd">
            <soap:address xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" location="http://localhost"/>
        </port>
    </service>
</definitions>"""


# ---------------------------------------------------------------------------
# JCA stubs
# ---------------------------------------------------------------------------

def _make_source_jca(conn_code: str, adapter_type: str, host: str,
                     port: str, extra: dict) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<adapter-config xmlns="http://platform.integration.oracle/blocks/adapter/fw/metadata"
                adapter="Cloud" adapterDisplayName="Cloud"
                wsdlLocation="SourceReceive_REQUEST.wsdl">
    <connection-factory location="cloud/CloudAdapter"
                        UIConnectionName="{conn_code}"/>
    <endpoint-interaction portType="SourceReceive_REQUEST_ptt" operation="receive">
        <interaction-spec className="oracle.cloud.connector.api.CloudInteractionSpec">
            <property name="AdapterServiceName" value="{adapter_type.lower()}"/>
            <property name="OperationName" value="receive"/>
            <property name="ConnectionCode" value="{conn_code}"/>
            <property name="host" value="{host}"/>
            <property name="port" value="{port}"/>
        </interaction-spec>
    </endpoint-interaction>
</adapter-config>"""


def _make_target_jca(conn_code: str, adapter_type: str, host: str,
                     port: str, extra: dict) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<adapter-config xmlns="http://platform.integration.oracle/blocks/adapter/fw/metadata"
                adapter="Cloud" adapterDisplayName="Cloud"
                wsdlLocation="TargetInvoke_REQUEST.wsdl">
    <connection-factory location="cloud/CloudAdapter"
                        UIConnectionName="{conn_code}"/>
    <endpoint-interaction portType="TargetInvoke_REQUEST_ptt" operation="execute">
        <interaction-spec className="oracle.cloud.connector.api.CloudInteractionSpec">
            <property name="AdapterServiceName" value="{adapter_type.lower()}"/>
            <property name="OperationName" value="execute"/>
            <property name="ConnectionCode" value="{conn_code}"/>
            <property name="host" value="{host}"/>
            <property name="port" value="{port}"/>
        </interaction-spec>
    </endpoint-interaction>
</adapter-config>"""


# ---------------------------------------------------------------------------
# XSLT mapping
# ---------------------------------------------------------------------------

def _make_xslt_mappings(field_mappings: list,
                         source_conn_code: str,
                         target_conn_code: str) -> str:
    """Build XSLT 1.0 mapping stylesheet."""
    field_lines = ""
    for m in (field_mappings or []):
        src = m.get("source", "")
        tgt = m.get("target", "")
        data_type = m.get("dataType", "STRING")
        if data_type.upper() in ("DECIMAL", "NUMBER", "INTEGER"):
            field_lines += (
                f'        <{tgt}><xsl:value-of select="number($src/{src})"/></{tgt}>\n'
            )
        else:
            field_lines += (
                f'        <{tgt}><xsl:value-of select="$src/{src}"/></{tgt}>\n'
            )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ics="http://www.oracle.com/2014/03/ic/integration/metadata"
    exclude-result-prefixes="ics">
    <xsl:template match="/">
        <xsl:variable name="src" select="/"/>
        <TargetRequest>
{field_lines}        </TargetRequest>
    </xsl:template>
</xsl:stylesheet>"""


# ---------------------------------------------------------------------------
# icspackage/icspackage.xml  (CORRECT manifest format)
# ---------------------------------------------------------------------------

def _make_icspackage_xml(project_code: str, version: str,
                          source_conn_code: str,
                          target_conn_code: str) -> str:
    """
    The manifest must list integrations AND connections.
    Version must match the folder name suffix exactly.
    """
    version = _normalize_ver(version)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<icspackage xmlns="http://xmlns.oracle.com/ics/package">
  <integrations>
    <integration>
      <code>{project_code}</code>
      <version>{version}</version>
    </integration>
  </integrations>
  <connections>
    <connection>
      <code>{source_conn_code}</code>
    </connection>
    <connection>
      <code>{target_conn_code}</code>
    </connection>
  </connections>
</icspackage>"""


# ---------------------------------------------------------------------------
# Main ZIP builder
# ---------------------------------------------------------------------------

def build_iar_zip(req: dict) -> bytes:
    """
    Build an OIC-compliant IAR ZIP file.

    Correct structure (based on reference oicdash IAR):
    icspackage/
        icspackage.xml
        appinstances/
            SOURCE_CONN_CODE.xml      <- ApplicationInstance format
            TARGET_CONN_CODE.xml
        project/
            PROJECT_CODE_VV.VV.VVVV/     <- folder name = code_version
                ics_project_attributes.properties
                PROJECT-INF/
                    project.xml
                    analysis.json
                    layout3.json
                    project_messages.json
                resources/
                    processor_1/resourcegroup_2/
                        ICSIntegrationMetadata.xsd
                    processor_30/resourcegroup_31/
                        ICSFault.xsd
                    processor_40/resourcegroup_41/
                        mapping.xsl
                    application_10/outbound_12/resourcegroup_11/
                        SourceReceive_REQUEST.wsdl
                        SourceReceive_REQUEST.jca
                    application_20/inbound_22/resourcegroup_21/
                        TargetInvoke_REQUEST.wsdl
                        TargetInvoke_REQUEST.jca
                        ICSFault.xsd
    """
    version = _normalize_ver(req.get("version", "01.00.0000"))
    project_code = _safe_id(req["integration_name"])
    project_name = req["integration_name"]
    description = req.get("description", "")

    source_conn_code = _safe_id(req.get("source_conn_name",
                                         f"{project_code}_SOURCE"))
    target_conn_code = _safe_id(req.get("target_conn_name",
                                         f"{project_code}_TARGET"))

    source_type = req.get("source_type", "SFTP")
    target_type = req.get("target_type", "ORACLE")
    source_host = req.get("source_host", "sftp.example.com")
    source_port = str(req.get("source_port", "22"))
    target_host = req.get("target_host", "oracle.example.com")
    target_port = str(req.get("target_port", "1521"))
    source_extra = req.get("source_extra", {})
    target_extra = req.get("target_extra", {})
    field_mappings = req.get("field_mappings", [])

    # The project folder name MUST include the version suffix
    project_folder = f"icspackage/project/{project_code}_{version}/"
    res_base = project_folder + "resources/"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # ---- icspackage.xml (manifest) ----
        zf.writestr(
            "icspackage/icspackage.xml",
            _make_icspackage_xml(project_code, version,
                                 source_conn_code, target_conn_code)
        )

        # ---- appinstances (correct ApplicationInstance format) ----
        zf.writestr(
            f"icspackage/appinstances/{source_conn_code}.xml",
            _make_app_instance_xml(
                conn_code=source_conn_code,
                display_name=source_conn_code,
                adapter_type=source_type,
                host=source_host,
                port=source_port,
                extra=source_extra,
                role="SOURCE_AND_TARGET"
            )
        )
        zf.writestr(
            f"icspackage/appinstances/{target_conn_code}.xml",
            _make_app_instance_xml(
                conn_code=target_conn_code,
                display_name=target_conn_code,
                adapter_type=target_type,
                host=target_host,
                port=target_port,
                extra=target_extra,
                role="SOURCE_AND_TARGET"
            )
        )

        # ---- ics_project_attributes.properties (CORRECT key names) ----
        zf.writestr(
            project_folder + "ics_project_attributes.properties",
            _make_project_attributes(project_code, project_name,
                                     version, description)
        )

        # ---- PROJECT-INF/ ----
        zf.writestr(
            project_folder + "PROJECT-INF/project.xml",
            _make_project_xml(
                project_code=project_code,
                project_name=project_name,
                version=version,
                source_conn_code=source_conn_code,
                source_adapter_type=source_type,
                target_conn_code=target_conn_code,
                target_adapter_type=target_type,
                field_mappings=field_mappings,
                description=description
            )
        )
        zf.writestr(
            project_folder + "PROJECT-INF/analysis.json",
            _make_analysis_json(project_code, version)
        )
        zf.writestr(
            project_folder + "PROJECT-INF/layout3.json",
            _make_layout_json()
        )
        zf.writestr(
            project_folder + "PROJECT-INF/project_messages.json",
            _make_project_messages_json()
        )

        # ---- resources/processor_1 — ICSIntegrationMetadata.xsd ----
        zf.writestr(
            res_base + "processor_1/resourcegroup_2/ICSIntegrationMetadata.xsd",
            ICS_METADATA_XSD
        )

        # ---- resources/processor_30 — global catch ICSFault.xsd ----
        zf.writestr(
            res_base + "processor_30/resourcegroup_31/ICSFault.xsd",
            ICS_FAULT_XSD
        )

        # ---- resources/processor_40 — XSLT mapping ----
        zf.writestr(
            res_base + "processor_40/resourcegroup_41/mapping.xsl",
            _make_xslt_mappings(field_mappings, source_conn_code, target_conn_code)
        )

        # ---- resources/application_10 — source WSDL + JCA ----
        src_rg = res_base + "application_10/outbound_12/resourcegroup_11/"
        zf.writestr(
            src_rg + "SourceReceive_REQUEST.wsdl",
            _make_source_wsdl(project_code, source_type)
        )
        zf.writestr(
            src_rg + "SourceReceive_REQUEST.jca",
            _make_source_jca(source_conn_code, source_type,
                             source_host, source_port, source_extra)
        )

        # ---- resources/application_20 — target WSDL + JCA + ICSFault.xsd ----
        tgt_rg = res_base + "application_20/inbound_22/resourcegroup_21/"
        zf.writestr(
            tgt_rg + "TargetInvoke_REQUEST.wsdl",
            _make_target_wsdl(project_code, target_type)
        )
        zf.writestr(
            tgt_rg + "TargetInvoke_REQUEST.jca",
            _make_target_jca(target_conn_code, target_type,
                             target_host, target_port, target_extra)
        )
        zf.writestr(tgt_rg + "ICSFault.xsd", ICS_FAULT_XSD)

    return buf.getvalue()


# ---------------------------------------------------------------------------
# OIC LLM Agent
# ---------------------------------------------------------------------------

class OICLLMAgent:
    """LLM Agent for generating OIC IAR files using Cohere."""

    def __init__(self):
        self.api_key = os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError("COHERE_API_KEY not set in environment")
        self.client = cohere.ClientV2(api_key=self.api_key)
        self.model = "command-a-plus-05-2026"

    def _extract_text(self, response) -> str:
        try:
            if hasattr(response, "message") and hasattr(response.message, "content"):
                content = response.message.content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        item_type = (
                            item.type if hasattr(item, "type")
                            else item.get("type", "") if isinstance(item, dict)
                            else ""
                        )
                        if item_type == "thinking":
                            continue
                        if hasattr(item, "text"):
                            parts.append(item.text)
                        elif isinstance(item, dict) and "text" in item:
                            parts.append(item["text"])
                    return "\n".join(parts)
                if isinstance(content, str):
                    return content
                if hasattr(content, "text"):
                    return content.text
            if hasattr(response, "text"):
                return response.text
            return str(response)
        except Exception as e:
            raise ValueError(f"Could not extract text from response: {e}")

    def _extract_requirements(self, user_instructions: str) -> dict:
        prompt = f"""You are an Oracle Integration Cloud (OIC) architect.
Extract integration requirements from the user instructions.
Return ONLY a valid JSON object — no markdown fences, no explanation, no preamble.

JSON schema:
{{
  "integration_name": "SFTPtoOracleGL",
  "description": "SFTP CSV to Oracle GL Journal Import",
  "version": "01.00.0000",
  "source_type": "SFTP",
  "source_conn_name": "SFTP_SOURCE_CONN",
  "source_host": "sftp.example.com",
  "source_port": "22",
  "source_extra": {{"directory": "/incoming", "filename": "*.csv"}},
  "target_type": "ERP",
  "target_conn_name": "ORACLE_GL_TARGET_CONN",
  "target_host": "oracle.example.com",
  "target_port": "443",
  "target_extra": {{"schema": "GL"}},
  "field_mappings": [
    {{"source": "journal_name", "target": "JE_BATCH_NAME", "dataType": "STRING"}},
    {{"source": "period", "target": "PERIOD_NAME", "dataType": "STRING"}},
    {{"source": "account_code", "target": "CODE_COMBINATION_ID", "dataType": "STRING"}},
    {{"source": "debit_amount", "target": "ENTERED_DR", "dataType": "DECIMAL"}},
    {{"source": "credit_amount", "target": "ENTERED_CR", "dataType": "DECIMAL"}},
    {{"source": "description", "target": "DESCRIPTION", "dataType": "STRING"}},
    {{"source": "currency", "target": "CURRENCY_CODE", "dataType": "STRING"}}
  ]
}}

Rules:
- integration_name: PascalCase, no spaces
- source_conn_name / target_conn_name: UPPER_SNAKE_CASE codes
- version: always "01.00.0000"
- source_type / target_type: one of SFTP, FTP, REST, SOAP, ERP, ORACLE, DB, FILE
- source_port: string
- target_port: string

USER INSTRUCTIONS:
{user_instructions}

Output ONLY the JSON object, nothing else."""

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = self._extract_text(response).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    def generate_integration_code(self,
                                   user_instructions: str
                                   ) -> Tuple[bool, Dict[str, Any]]:
        try:
            print("Step 1/2 — Extracting requirements from instructions...")
            req = self._extract_requirements(user_instructions)
            req["version"] = _normalize_ver(req.get("version", "01.00.0000"))
            project_code = _safe_id(req["integration_name"])

            print(f"  Integration : {req['integration_name']} ({project_code})")
            print(f"  Version     : {req['version']}")
            print(f"  Source      : {req['source_type']} @ {req['source_host']}:{req['source_port']}")
            print(f"  Target      : {req['target_type']} @ {req['target_host']}:{req['target_port']}")
            print(f"  Mappings    : {len(req.get('field_mappings', []))} fields")

            print("Step 2/2 — Building IAR ZIP with correct OIC structure...")
            iar_bytes = build_iar_zip(req)

            # IAR filename: CODE_VVVVVVVV.iar  (version digits without dots)
            ver_digits = req["version"].replace(".", "")
            filename = f"{project_code}_{ver_digits}.iar"

            return True, {
                "success": True,
                "filename": filename,
                "iar_bytes": iar_bytes,
                "requirements": req,
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
            }

        except json.JSONDecodeError as e:
            return False, {"error": f"LLM returned invalid JSON: {e}"}
        except Exception as e:
            import traceback
            return False, {"error": str(e), "traceback": traceback.format_exc()}

    def generate_integration_with_chat(self,
                                        user_message: str,
                                        conversation_history: list
                                        ) -> Tuple[str, list]:
        system_prompt = """You are an OIC (Oracle Integration Cloud) expert.
Help users define their integration requirements by asking about:
1. Source system type and connection details (SFTP, REST, ERP, DB, etc.)
2. Target system type and connection details
3. Data fields to map between source and target
4. Any error handling or transformation requirements

Be conversational. When you have enough information, say:
"I have all the information I need! Ready to generate the IAR file!"
"""
        full_prompt = system_prompt + "\nConversation:\n"
        for msg in conversation_history:
            full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
        full_prompt += f"USER: {user_message}"

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}]
            )
            assistant_msg = self._extract_text(response).strip()
            updated_history = conversation_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_msg},
            ]
            return assistant_msg, updated_history
        except Exception as e:
            return f"Error: {e}", conversation_history