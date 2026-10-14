import{c as o,V as n,W as i}from"./index-DLlmPWom.js";/**
 * @license lucide-react v0.441.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const e=o("Pause",[["rect",{x:"14",y:"4",width:"4",height:"16",rx:"1",key:"zuxfzm"}],["rect",{x:"6",y:"4",width:"4",height:"16",rx:"1",key:"1okwgv"}]]);/**
 * @license lucide-react v0.441.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const r=o("Play",[["polygon",{points:"6 3 20 12 6 21 6 3",key:"1oa8hb"}]]),p={async listApps(t={}){return n(`/monitoring/apps${i(t)}`)},async addApp(t){return n("/monitoring/apps",{method:"POST",body:JSON.stringify(t)})},async updateApp(t,s){return n(`/monitoring/apps/${t}`,{method:"PATCH",body:JSON.stringify(s)})},async removeApp(t){await n(`/monitoring/apps/${t}`,{method:"DELETE"})},async syncApp(t){return n(`/monitoring/apps/${t}/sync`,{method:"POST",body:JSON.stringify({})})}};export{e as P,r as a,p as m};
