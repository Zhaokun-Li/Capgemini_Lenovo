import request from './request.js'


export function getOpinions() {
  return request({
    url: '/api/opinions',
    method: 'get'
  })
}


export function addOpinion(data) {
  return request({
    url: '/api/opinions',
    method: 'post',
    data
  })
}


export function deleteOpinion(id) {
  return request({
    url: `/api/opinions/${id}`,
    method: 'delete'
  })
}