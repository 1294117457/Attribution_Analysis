import { createRouter, createWebHistory } from 'vue-router'
import CollectPage from '../views/CollectPage.vue'
import ManagePage from '../views/ManagePage.vue'

const routes = [
  { path: '/', component: CollectPage },
  { path: '/manage', component: ManagePage },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
