"use strict";(self["webpackChunkvideo_streaming"]=self["webpackChunkvideo_streaming"]||[]).push([[443],{9381:function(e,t,a){a.r(t),a.d(t,{default:function(){return N}});var l=a(3396),i=a(7139),r=a(702),s=a(3369),n=a(3289),u=a(3947),o=a(4960),d=a(2718),v=a(9166),c=a(9694),f=a(2465),p=a(4231),g=a(9374),h=a(1138),m=a(7041),_=a(5221),b=a(6107),w=a(8157),y=a(1629),x=a(8717),L=a(4870);function W(){const e=(0,L.iH)([]);function t(t,a){e.value[a]=t}return(0,l.Xn)((()=>e.value=[])),{refs:e,updateRef:t}}var k=a(3712),$=a(1107),V=a(131),D=a(9888);const A=(0,$.ev)()({name:"VPagination",props:{activeColor:String,start:{type:[Number,String],default:1},modelValue:{type:Number,default:e=>e.start},disabled:Boolean,length:{type:[Number,String],default:1,validator:e=>e%1===0},totalVisible:[Number,String],firstIcon:{type:o.lE,default:"$first"},prevIcon:{type:o.lE,default:"$prev"},nextIcon:{type:o.lE,default:"$next"},lastIcon:{type:o.lE,default:"$last"},ariaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.root"},pageAriaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.page"},currentPageAriaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.currentPage"},firstAriaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.first"},previousAriaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.previous"},nextAriaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.next"},lastAriaLabel:{type:String,default:"$vuetify.pagination.ariaLabel.last"},ellipsis:{type:String,default:"..."},showFirstLastPage:Boolean,...(0,d.m)(),...(0,v.l)(),...(0,c.f)(),...(0,f.c)(),...(0,p.I)(),...(0,g.Z)(),...(0,h.Q)({tag:"nav"}),...(0,m.x$)(),...(0,_.bk)({variant:"text"})},emits:{"update:modelValue":e=>!0,first:e=>!0,prev:e=>!0,next:e=>!0,last:e=>!0},setup(e,t){let{slots:a,emit:i}=t;const s=(0,x.z)(e,"modelValue"),{t:n,n:u}=(0,y.bU)(),{isRtl:o}=(0,y.Vw)(),{themeClasses:d}=(0,m.ER)(e),{width:v}=(0,w.AW)(),c=(0,L.iH)(-1);(0,b.AF)(void 0,{scoped:!0});const{resizeRef:f}=(0,k.y)((e=>{if(!e.length)return;const{target:t,contentRect:a}=e[0],l=t.querySelector(".v-pagination__list > *");if(!l)return;const i=a.width,r=l.offsetWidth+2*parseFloat(getComputedStyle(l).marginRight);c.value=_(i,r)})),p=(0,l.Fl)((()=>parseInt(e.length,10))),g=(0,l.Fl)((()=>parseInt(e.start,10))),h=(0,l.Fl)((()=>e.totalVisible?parseInt(e.totalVisible,10):c.value>=0?c.value:_(v.value,58)));function _(t,a){const l=e.showFirstLastPage?5:3;return Math.max(0,Math.floor(+((t-a*l)/a).toFixed(2)))}const $=(0,l.Fl)((()=>{if(p.value<=0||isNaN(p.value)||p.value>Number.MAX_SAFE_INTEGER)return[];if(h.value<=1)return[s.value];if(p.value<=h.value)return(0,V.MT)(p.value,g.value);const t=h.value%2===0,a=t?h.value/2:Math.floor(h.value/2),l=t?a:a+1,i=p.value-a;if(l-s.value>=0)return[...(0,V.MT)(Math.max(1,h.value-1),g.value),e.ellipsis,p.value];if(s.value-i>=(t?1:0)){const t=h.value-1,a=p.value-t+g.value;return[g.value,e.ellipsis,...(0,V.MT)(t,a)]}{const t=Math.max(1,h.value-3),a=1===t?s.value:s.value-Math.ceil(t/2)+g.value;return[g.value,e.ellipsis,...(0,V.MT)(t,a),e.ellipsis,p.value]}}));function A(e,t,a){e.preventDefault(),s.value=t,a&&i(a,t)}const{refs:F,updateRef:I}=W();(0,b.AF)({VPaginationBtn:{color:(0,L.Vh)(e,"color"),border:(0,L.Vh)(e,"border"),density:(0,L.Vh)(e,"density"),size:(0,L.Vh)(e,"size"),variant:(0,L.Vh)(e,"variant"),rounded:(0,L.Vh)(e,"rounded"),elevation:(0,L.Vh)(e,"elevation")}});const C=(0,l.Fl)((()=>$.value.map(((t,a)=>{const l=e=>I(e,a);if("string"===typeof t)return{isActive:!1,key:`ellipsis-${a}`,page:t,props:{ref:l,ellipsis:!0,icon:!0,disabled:!0}};{const a=t===s.value;return{isActive:a,key:t,page:u(t),props:{ref:l,ellipsis:!1,icon:!0,disabled:!!e.disabled||+e.length<2,color:a?e.activeColor:e.color,ariaCurrent:a,ariaLabel:n(a?e.currentPageAriaLabel:e.pageAriaLabel,t),onClick:e=>A(e,t)}}}})))),S=(0,l.Fl)((()=>{const t=!!e.disabled||s.value<=g.value,a=!!e.disabled||s.value>=g.value+p.value-1;return{first:e.showFirstLastPage?{icon:o.value?e.lastIcon:e.firstIcon,onClick:e=>A(e,g.value,"first"),disabled:t,ariaLabel:n(e.firstAriaLabel),ariaDisabled:t}:void 0,prev:{icon:o.value?e.nextIcon:e.prevIcon,onClick:e=>A(e,s.value-1,"prev"),disabled:t,ariaLabel:n(e.previousAriaLabel),ariaDisabled:t},next:{icon:o.value?e.prevIcon:e.nextIcon,onClick:e=>A(e,s.value+1,"next"),disabled:a,ariaLabel:n(e.nextAriaLabel),ariaDisabled:a},last:e.showFirstLastPage?{icon:o.value?e.firstIcon:e.lastIcon,onClick:e=>A(e,g.value+p.value-1,"last"),disabled:a,ariaLabel:n(e.lastAriaLabel),ariaDisabled:a}:void 0}}));function P(){const e=s.value-g.value;F.value[e]?.$el.focus()}function T(t){t.key===V.ff.left&&!e.disabled&&s.value>+e.start?(s.value=s.value-1,(0,l.Y3)(P)):t.key===V.ff.right&&!e.disabled&&s.value<g.value+p.value-1&&(s.value=s.value+1,(0,l.Y3)(P))}return(0,D.L)((()=>(0,l.Wm)(e.tag,{ref:f,class:["v-pagination",d.value,e.class],style:e.style,role:"navigation","aria-label":n(e.ariaLabel),onKeydown:T,"data-test":"v-pagination-root"},{default:()=>[(0,l.Wm)("ul",{class:"v-pagination__list"},[e.showFirstLastPage&&(0,l.Wm)("li",{key:"first",class:"v-pagination__first","data-test":"v-pagination-first"},[a.first?a.first(S.value.first):(0,l.Wm)(r.T,(0,l.dG)({_as:"VPaginationBtn"},S.value.first),null)]),(0,l.Wm)("li",{key:"prev",class:"v-pagination__prev","data-test":"v-pagination-prev"},[a.prev?a.prev(S.value.prev):(0,l.Wm)(r.T,(0,l.dG)({_as:"VPaginationBtn"},S.value.prev),null)]),C.value.map(((e,t)=>(0,l.Wm)("li",{key:e.key,class:["v-pagination__item",{"v-pagination__item--is-active":e.isActive}],"data-test":"v-pagination-item"},[a.item?a.item(e):(0,l.Wm)(r.T,(0,l.dG)({_as:"VPaginationBtn"},e.props),{default:()=>[e.page]})]))),(0,l.Wm)("li",{key:"next",class:"v-pagination__next","data-test":"v-pagination-next"},[a.next?a.next(S.value.next):(0,l.Wm)(r.T,(0,l.dG)({_as:"VPaginationBtn"},S.value.next),null)]),e.showFirstLastPage&&(0,l.Wm)("li",{key:"last",class:"v-pagination__last","data-test":"v-pagination-last"},[a.last?a.last(S.value.last):(0,l.Wm)(r.T,(0,l.dG)({_as:"VPaginationBtn"},S.value.last),null)])])]}))),{}}}),F=(0,$.ev)()({name:"VTable",props:{fixedHeader:Boolean,fixedFooter:Boolean,height:[Number,String],hover:Boolean,...(0,v.l)(),...(0,c.f)(),...(0,h.Q)(),...(0,m.x$)()},setup(e,t){let{slots:a}=t;const{themeClasses:i}=(0,m.ER)(e),{densityClasses:r}=(0,c.t)(e);return(0,D.L)((()=>(0,l.Wm)(e.tag,{class:["v-table",{"v-table--fixed-height":!!e.height,"v-table--fixed-header":e.fixedHeader,"v-table--fixed-footer":e.fixedFooter,"v-table--has-top":!!a.top,"v-table--has-bottom":!!a.bottom,"v-table--hover":e.hover},i.value,r.value,e.class],style:e.style},{default:()=>[a.top?.(),a.default?(0,l.Wm)("div",{class:"v-table__wrapper",style:{height:(0,V.kb)(e.height)}},[(0,l.Wm)("table",null,[a.default()])]):a.wrapper?.(),a.bottom?.()]}))),{}}}),I={class:"d-flex"},C=(0,l._)("h1",null,"History",-1),S=(0,l._)("thead",null,[(0,l._)("tr",null,[(0,l._)("th",{class:"text-left"}),(0,l._)("th",{class:"text-left"},"Date"),(0,l._)("th",{class:"text-left"},"Weight"),(0,l._)("th",{class:"text-left"},"Length"),(0,l._)("th",{class:"text-left"},"Height"),(0,l._)("th",{class:"text-left"})])],-1);function P(e,t,a,o,d,v){return(0,l.wg)(),(0,l.j4)(s.K,null,{default:(0,l.w5)((()=>[(0,l._)("div",I,[(0,l.Wm)(r.T,{to:"/",size:"x-large",variant:"plain"},{default:(0,l.w5)((()=>[(0,l.Wm)(n.t,null,{default:(0,l.w5)((()=>[(0,l.Uk)("mdi-arrow-left")])),_:1})])),_:1}),C]),(0,l.Wm)(F,{"fixed-header":""},{default:(0,l.w5)((()=>[S,(0,l._)("tbody",null,[((0,l.wg)(!0),(0,l.iD)(l.HY,null,(0,l.Ko)(e.muestras,(e=>((0,l.wg)(),(0,l.iD)("tr",{key:e.id},[(0,l._)("td",null,[(0,l.Wm)(u.f,{src:`http://127.0.0.1:${this.url_port}/muestra_image/${e.image}`,width:"150",height:"150",contain:""},null,8,["src"])]),(0,l._)("td",null,(0,i.zw)(e.date),1),(0,l._)("td",null,(0,i.zw)(e.weight),1),(0,l._)("td",null,(0,i.zw)(e.length),1),(0,l._)("td",null,(0,i.zw)(e.height),1),(0,l._)("td",null,[(0,l.Wm)(r.T,{to:`/muestra/${e.id}`,size:"x-large",variant:"plain"},{default:(0,l.w5)((()=>[(0,l.Wm)(n.t,null,{default:(0,l.w5)((()=>[(0,l.Uk)("mdi-arrow-right")])),_:1})])),_:2},1032,["to"])])])))),128))])])),_:1}),(0,l.Wm)(A,{modelValue:e.page,"onUpdate:modelValue":t[0]||(t[0]=t=>e.page=t),length:4,rounded:"circle"},null,8,["modelValue"])])),_:1})}var T=a(4161),z=a(1073),M={name:"History",data:()=>({muestras:[],page:1}),computed:{url_server(){return z["default"].url_server()},url_port(){return z["default"].url_port()}},methods:{fetchData(){const{url_server:e,page:t}=this;console.warn(`http://127.0.0.1:${this.url_port}/history/${t}`),T.Z.get(`http://127.0.0.1:${this.url_port}/history/${t}`).then((e=>{console.warn(e.data.data),this.muestras=e.data.data})).catch((e=>{console.log(e)}))}},mounted(){this.fetchData()},watch:{page(){this.fetchData()}}},B=a(89);const E=(0,B.Z)(M,[["render",P]]);var N=E},8364:function(e,t,a){a.r(t),a.d(t,{default:function(){return x}});var l=a(3396),i=a(7139),r=a(702),s=a(3369),n=a(6824),u=a(8521),o=a(3289);const d=e=>((0,l.dD)("data-v-7bb8973c"),e=e(),(0,l.Cn)(),e),v={class:"d-flex"},c=d((()=>(0,l._)("h1",null,"Details",-1))),f=["src"],p=d((()=>(0,l._)("h2",null,"Weight:",-1))),g={class:"ml-3"};function h(e,t,a,d,h,m){return(0,l.wg)(),(0,l.j4)(s.K,null,{default:(0,l.w5)((()=>[(0,l._)("div",v,[(0,l.Wm)(r.T,{to:"/history",size:"x-large",variant:"plain"},{default:(0,l.w5)((()=>[(0,l.Wm)(o.t,null,{default:(0,l.w5)((()=>[(0,l.Uk)("mdi-arrow-left")])),_:1})])),_:1}),c]),e.muestra?((0,l.wg)(),(0,l.j4)(n.o,{key:0},{default:(0,l.w5)((()=>[(0,l.Wm)(u.D,{class:"",cols:"6"},{default:(0,l.w5)((()=>[(0,l._)("img",{class:"the_fuckin_image",src:`http://127.0.0.1:${this.url_port}/muestra_image/${e.muestra.image}`,crossorigin:"anonymous"},null,8,f)])),_:1})])),_:1})):(0,l.kq)("",!0),e.muestra?((0,l.wg)(),(0,l.j4)(n.o,{key:1},{default:(0,l.w5)((()=>[(0,l.Wm)(u.D,{cols:"6",class:"d-flex flex-column"},{default:(0,l.w5)((()=>[p,(0,l._)("h1",g,(0,i.zw)(e.muestra.weight)+"G",1),(0,l.Wm)(u.D,{cols:"12",class:"d-flex"},{default:(0,l.w5)((()=>[(0,l.Wm)(n.o,null,{default:(0,l.w5)((()=>[((0,l.wg)(!0),(0,l.iD)(l.HY,null,(0,l.Ko)(e.indicators,((e,t)=>((0,l.wg)(),(0,l.j4)(u.D,{cols:"2",class:"d-flex flex-column align-center px-3 indicator-wrapper"},{default:(0,l.w5)((()=>[(0,l._)("span",{class:(0,i.C_)("text-"+(e?"black":"grey"))}," Indicator "+(0,i.zw)(t+1),3),(0,l._)("div",{class:(0,i.C_)(["indicator",e?"active":"inactive"])},null,2)])),_:2},1024)))),256))])),_:1})])),_:1})])),_:1})])),_:1})):(0,l.kq)("",!0)])),_:1})}var m=a(4161),_=a(1073),b={name:"Muestra",data:()=>({muestra:null,indicators:[]}),computed:{url_server(){return _["default"].url_server()},url_port(){return _["default"].url_port()}},methods:{fetchData(){const{url_port:e,page:t}=this;m.Z.get(`http://127.0.0.1:${e}/select/${this.$route.params.id}`).then((e=>{console.warn(e.data.data),this.muestra=e.data.data[0];const t=JSON.parse(`[${this.muestra.defects}]`);t.forEach((e=>{this.indicators[e]=!0}))})).catch((e=>{console.error(e)}))}},mounted(){this.fetchData();var{noOfDefects:e}=_["default"];this.indicators=[...new Array(e).fill(!1)]},watch:{muestra:function(e){console.warn(e)},"$route.params.id":function(e){console.warn(e),this.fetchData()}}},w=a(89);const y=(0,w.Z)(b,[["render",h],["__scopeId","data-v-7bb8973c"]]);var x=y}}]);
//# sourceMappingURL=about.1a88f69b.js.map